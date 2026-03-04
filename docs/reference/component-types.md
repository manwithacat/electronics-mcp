# Component Types

The full hierarchy of supported component types in ElectronicsMCP.

## Passive

- **resistor** -- `resistance`, optional `tolerance`, `power_rating`, `temp_coeff`
- **capacitor** -- `capacitance`, optional `esr`, `voltage_rating`, `dielectric`
- **inductor** -- `inductance`, optional `dcr`, `saturation_current`, `srf`
- **potentiometer** -- `resistance`, `wiper_position`
- **fuse** -- `rating`, optional `type` (fast/slow)
- **crystal** -- `frequency`, optional `load_capacitance`

## Source

- **voltage_source** -- subtypes: `dc`, `ac`, `pulse`, `pwl`, `custom`
- **current_source** -- subtypes: `dc`, `ac`, `pulse`, `pwl`, `custom`
- **dependent_source** -- subtypes: `vcvs`, `vccs`, `ccvs`, `cccs` with `gain`

## Semiconductor

- **diode** -- `model` or `is`, `n`, `bv`
- **zener** -- `breakdown_voltage`, optional `model`
- **led** -- `forward_voltage`, `colour`
- **bjt** -- `npn`/`pnp`, `model` or `beta`, `vbe`
- **mosfet** -- `nmos`/`pmos`, `model` or `vth`, `rds_on`, `ciss`
- **jfet** -- `n`/`p`, `model` or `idss`, `vp`
- **igbt** -- `model`

## Integrated Circuit

- **opamp** -- `model`, optional `gbw`, `slew_rate`, `vos`, `ib`
- **comparator** -- `model`, optional `response_time`
- **voltage_regulator** -- `type` (linear/switching), `model`, optional `vin_range`, `vout`, `iout_max`
- **timer_555** -- no parameters (behaviour determined by external components)
- **custom_ic** -- `model`, `pinout` mapping pin names to nodes

## Subcircuit

References the subcircuit library by name, with parameter overrides and port connections.

## Transformer

- **transformer** -- `turns_ratio`, optional `primary_inductance`, `coupling`

## Electromechanical

- **relay** -- `coil_voltage`, `contact_config`
- **switch** -- `type` (spst/spdt/dpdt), optional `normally_open`
- **connector** -- `pins`
