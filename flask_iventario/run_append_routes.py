import os

target = r"c:\Cursos\Python\SummanPOS\flask_iventario\routes\dropshipping_routes.py"
append = r"c:\Cursos\Python\SummanPOS\flask_iventario\append_pdf_routes.py"

with open(append, "r", encoding="utf-8") as f:
    append_content = f.read()

with open(target, "a", encoding="utf-8") as f:
    f.write("\n" + append_content)
    
print("Routes appended!")
