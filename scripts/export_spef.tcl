# scripts/export_spef.tcl
if {![info exists ::env(SPEF_OUT)]} {
  error "SPEF_OUT is not set"
}
write_spef $::env(SPEF_OUT)
