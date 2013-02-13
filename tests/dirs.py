import os

def all_dirnames(directory):
    dirnames = [directory]
    while directory and directory != os.path.dirname(directory):
        directory = os.path.dirname(directory)
        dirnames.append(directory)
    return dirnames


if __name__ == "__main__":
    print all_dirnames(os.path.realpath(os.path.dirname(__file__)))
