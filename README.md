# spine-to-msm.py

A converter from Spine2D to the MSM binary format or whatever idk

Tested with [NPS](https://github.com/Next-Private-Server/Next-Private-Server)

**ONLY SPINE 3.8 SKELETONS WORK FOR NOW!!**

![gif](.github/gif.gif?raw=true)

## Usage

1. Grab the exported Spine JSON+atlas (EXPORTED WITH ROTATION OFF FOR ATLAS!), preferrably with **Premultiplied Alpha** off
2. Run the tool like `spine-to-msm.py "project.json" project.atlas.txt --out-bin project.bin --out-xml project.xml --scale 0.17`
3. Convert the PNG spritesheet into AVIF to work in-game
4. Add it to the game or idk whatever you're supposed to do after i just use NPS to replace the binary file, for those who don't understand - put the xml in `xml_resources/`, and bin in `xml_bin/` however you'd also need to add it to the server or you have to replace a monster's existing binary file so if you do just rename the bin file to match an existing monster

AssetRipper-exported Spine skeletons **do not** work!

## Credits

[Aniviewer](https://github.com/LennyFaze0/MSM-Aniviewer/tree/main/aniviewer) for `rev6_2_json.py` and `binfile.py`
