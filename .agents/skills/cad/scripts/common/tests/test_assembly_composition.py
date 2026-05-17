import json
import shutil
import struct
import unittest
from pathlib import Path

from common.assembly_composition import build_native_assembly_composition
from common.glb import read_step_topology_manifest_from_glb
from common.render import part_glb_path
from common.tests.cad_test_roots import IsolatedCadRoots


IDENTITY_TRANSFORM = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def _pad4(payload: bytes, *, byte: bytes = b"\0") -> bytes:
    padding = (4 - (len(payload) % 4)) % 4
    return payload + (byte * padding)


def _write_topology_glb(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_payload = json.dumps({"schemaVersion": 1, "profile": "index", **manifest}, separators=(",", ":")).encode("utf-8")
    binary = _pad4(manifest_payload)
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(manifest_payload)}],
        "extensionsUsed": ["STEP_topology"],
        "extensions": {
            "STEP_topology": {
                "schemaVersion": 1,
                "indexView": 0,
                "entryKind": "assembly" if manifest.get("assembly") else "part",
                "encoding": "utf-8",
            }
        },
    }
    json_chunk = _pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), byte=b" ")
    path.write_bytes(
        b"glTF"
        + struct.pack("<II", 2, 12 + 8 + len(json_chunk) + 8 + len(binary))
        + struct.pack("<I4s", len(json_chunk), b"JSON")
        + json_chunk
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )


class NativeAssemblyCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._isolated_roots = IsolatedCadRoots(self, prefix="assembly-composition-")
        tempdir = self._isolated_roots.temporary_cad_directory(prefix="tmp-assembly-composition-")
        self._tempdir = tempdir
        self.temp_root = Path(tempdir.name)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)
        self._tempdir.cleanup()

    def _write_step(self, name: str) -> Path:
        step_path = self.temp_root / f"{name}.step"
        step_path.write_text("ISO-10303-21; END-ISO-10303-21;\n", encoding="utf-8")
        return step_path

    def _write_topology(self, rows: list[list[object]]) -> Path:
        topology_path = part_glb_path(self.temp_root / "assembly.step")
        _write_topology_glb(
            topology_path,
            {
                "tables": {
                    "occurrenceColumns": [
                        "id",
                        "parentId",
                        "path",
                        "name",
                        "sourceName",
                        "transform",
                        "bbox",
                        "shapeCount",
                        "faceCount",
                        "edgeCount",
                    ]
                },
                "occurrences": rows,
            },
        )
        return topology_path

    def _assembly_mesh_path(self) -> Path:
        return part_glb_path(self.temp_root / "assembly.step")

    def _read_topology(self, topology_path: Path) -> dict[str, object]:
        manifest = read_step_topology_manifest_from_glb(topology_path)
        self.assertIsNotNone(manifest)
        assert manifest is not None
        return manifest

    def test_native_assembly_composition_declares_self_contained_mesh(self) -> None:
        self._write_step("assembly")
        topology_path = self._write_topology(
            [
                ["o1", "", "1", "root", "root", IDENTITY_TRANSFORM, None, 0, 0, 0, 0],
                [
                    "o1.1",
                    "o1",
                    "1.1",
                    "sample_component",
                    "SAMPLE_COMPONENT",
                    IDENTITY_TRANSFORM,
                    {"min": [0, 0, 0], "max": [1, 1, 1]},
                    1,
                    6,
                    12,
                    8,
                ],
            ]
        )

        payload = build_native_assembly_composition(
            cad_ref="imports/assembly",
            topology_path=topology_path,
            topology_manifest=self._read_topology(topology_path),
            mesh_path=self._assembly_mesh_path(),
        )

        self.assertEqual("native", payload["mode"])
        self.assertEqual("gltf-node-extras", payload["mesh"]["addressing"])
        root = payload["root"]
        self.assertEqual("assembly", root["displayName"])
        self.assertEqual(1, len(root["children"]))
        part = root["children"][0]
        self.assertEqual("part", part["nodeType"])
        self.assertEqual("sample_component", part["displayName"])

    def test_native_assembly_composition_falls_back_to_single_component(self) -> None:
        self._write_step("assembly")
        topology_path = self._write_topology(
            [
                [
                    "o1",
                    "",
                    "1",
                    "vendor-assembly",
                    "vendor-assembly",
                    IDENTITY_TRANSFORM,
                    {"min": [0, 0, 0], "max": [2, 2, 2]},
                    1,
                    12,
                    24,
                    16,
                ],
            ]
        )
        payload = build_native_assembly_composition(
            cad_ref="imports/assembly",
            topology_path=topology_path,
            topology_manifest=self._read_topology(topology_path),
            mesh_path=self._assembly_mesh_path(),
        )

        root = payload["root"]
        self.assertEqual(1, len(root["children"]))
        self.assertEqual("vendor-assembly", root["children"][0]["displayName"])
