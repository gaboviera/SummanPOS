import os

filepath = r"c:\Cursos\Python\SummanPOS\flask_iventario\models.py"
append_filepath = r"c:\Cursos\Python\SummanPOS\flask_iventario\append_dropshipping.py"

with open(append_filepath, "r", encoding="utf-8") as f:
    append_content = f.read()

with open(filepath, "a", encoding="utf-8") as f:
    f.write("\n" + append_content)
print("Restored Dropshipping models successfully!")
