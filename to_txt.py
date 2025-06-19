import glob

with open("test.txt", 'w', encoding='utf-8') as f_out:
    for file in glob.glob("**/*.py", recursive=True):
        if "__" in file or "site-packages" in file:
            continue
        print(file)
        f_out.write("######## Start file " + file + " ########\n")
        f_out.write("```Python\n")

        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                f_out.write(line)

        f_out.write("```\n")
        f_out.write("######## End file " + file + " ########\n\n\n\n")

print(">>> Done")