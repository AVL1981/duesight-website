@echo off
echo Kopieer top 10 designs naar duesight-website/designs/...
set SRC=C:\Users\arian\OneDrive\Desktop\DueSight website\stitch_duesight_background_design_proposals
set DST=C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-website\designs

if not exist "%DST%" mkdir "%DST%"

copy "%SRC%\animated_constellation_data_map\code.html" "%DST%\des-1.html"
copy "%SRC%\duesight_topography_hero_section\code.html" "%DST%\des-2.html"
copy "%SRC%\animated_financial_command_center\code.html" "%DST%\des-3.html"
copy "%SRC%\institutional_compliance_authority_section\code.html" "%DST%\des-4.html"
copy "%SRC%\trust_authority_section\code.html" "%DST%\des-5.html"
copy "%SRC%\sovereign_mesh_network_visualization\code.html" "%DST%\des-6.html"
copy "%SRC%\animated_neural_network_pulse\code.html" "%DST%\des-7.html"
copy "%SRC%\european_investment_constellation_map\code.html" "%DST%\des-8.html"
copy "%SRC%\animated_european_financial_network_hero\code.html" "%DST%\des-9.html"
copy "%SRC%\duesight_the_vault_hero_section_1\code.html" "%DST%\des-10.html"

echo.
echo Done! 10 designs gekopieerd naar %DST%
dir "%DST%\des-*.html"
pause
