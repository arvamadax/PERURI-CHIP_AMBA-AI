create_clock -name clk -period 10.000 [get_ports clk]
derive_clock_uncertainty
# Port bus virtual: tidak dibatasi waktu di fitting mandiri.
set_false_path -from [get_ports {rst address write writedata read}]
set_false_path -to [get_ports {readdata irq}]
