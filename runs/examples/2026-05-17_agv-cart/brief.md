# CAD brief: AGV cart

- **Model**: `agv_cart` blocky assembly
- **Task type**: hybrid constraint + Location assembly
- **Units**: mm
- **Coordinate convention**: origin at chassis geometric center; XY ground plane; +Z up
- **Overall dimensions**: chassis ~820×620×72; total height ~450 with mast
- **Functional features**:
  - Constraint region: `chassis` ground + 4×`wheel_*` corner placement on `chassis.+z`
  - Location region: deck, battery, drives, lidar mast, bumpers, skirts, rails, e-stop
- **Positioning**:
  - Wheels: contact + in_plane offsets at (±330, ±245); axis locks on chassis
  - Upper structure: formula heights from `CHASSIS_TOP_Z` and deck stack
- **STEP**: `examples/constraint/assemblies/agv_cart/model/agv_cart.step`
- **Validation**: `agv_cart_chassis.json` solve ok; `run_validation`; `inspect refs --facts --planes`
- **Assumptions**: block primitives only; stylized industrial AGV not curved sheet metal
