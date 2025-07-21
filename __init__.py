import requests, io, json
from PIL import Image, ImageTk, ImageDraw
from bs4 import BeautifulSoup
import networkx as nx
import matplotlib.pyplot as plt
import tkinter as tk

def startswith(str, seg):
    return str[0:len(seg)] == seg

def getDomain(url):
    return "/".join(url.split("/")[0:3])

def validate(url, root=""):
    url = url.split("?")[0].split("#")[0]
    if startswith(url, "https://") or startswith(url, "http://"):
        return url
    if startswith(url, "/"):
        return getDomain(root) + url
    #else it starts with nothing, it's a page in the same directory
    root = root.split("/")
    root[-1] = ""
    root = "/".join(root)
    return root + url

def relativeLinkRemoval(url):
    final = []
    url = url.split("/")
    for seg in url:
        if seg == "..":
            final.pop(0)
            continue
        elif seg == ".":
            continue
        final.append(seg)
    return "/".join(final)

class Page:
    def __init__(self, url):
        self.url = url
        self.__hyperlinks = False
    
    @property
    def hyperlinks(self):
        '''The hyperlinks on this object'''
        return self.__hyperlinks
    
    @hyperlinks.getter
    def hyperlinks(self):
        try:
            if not type(self.__hyperlinks) == list:
                self.__hyperlinks = self.findHyperlinks()
            return self.__hyperlinks
        except Exception as e:
            raise e
    
    @hyperlinks.setter
    def hyperlinks(self, value):
        self.__hyperlinks = value
    
    @hyperlinks.deleter
    def hyperlinks(self):
        self.__hyperlinks = False

    def findHyperlinks(self):
        url = self.url
        if "mailto:" in url:
            raise Exception(f"{url} is a mailto link")
        print(f"Loading {url}...")
        req = requests.get(url, timeout=3)
        if not req.ok:
            raise Exception(f"Response gave {req.status_code}: {req.reason}")
        content = BeautifulSoup(str(req.content), "html.parser")
        links = []
        for link in content.find_all('a'):
            try:
                link = validate(link.get('href'), url)
                linkRoot = getDomain(link)
                if not linkRoot in domains:
                    domains[linkRoot] = []
                if domainLock:
                    if not linkRoot == rootDomain:
                        continue
                if (not link in links) and (not len(domains[linkRoot]) == limit):
                    domains[linkRoot].append(link)
                    if len(domains[linkRoot]) == limit:
                        print(f"{linkRoot} limit reached")
                        break
                    links.append(relativeLinkRemoval(link))
            except Exception as e:
                if link == None:
                    # <a> missing a href. because of course it is. 
                    pass
                if e == KeyboardInterrupt:
                    stop()
                    break
                else:
                    print(e)
        if links == []:
            raise Exception("No links in document")
        return links

class Stack:
    items = []
    def read(self):
        return self.items[-1]
    def write(self, item):
        self.items.append(item)
    def remove(self):
        self.items.pop(-1)

class Queue:
    items = []
    def read(self):
        return self.items[0]
    def write(self, item):
        self.items.append(item)
    def remove(self):
        self.items.pop(0)

url = input("Input the starter URL:\n")
if not (startswith(url, "https://") or startswith(url, "http://")):
    url = f"https://{url}"

url = validate(url)

global running
while running := True:
    dorb = (input("Depth-first or breadth-first? d/b\n") + " ").lower()[0] 
    match dorb:
        case "b":
            dorb = "breadth"
            pages = Queue()
            break
        case "d":
            dorb = "depth"
            pages = Stack()
            break
        case _:
            dorb = "depth"
            pages = Stack()
            print("No decision made, defaulting to depth...")
            break

try:
    limit = int(input("Max number of urls from a domain? Leave blank for none\n"))
except:
    limit = 2**32

domainLock = (input("Only check URLs from the domain the link came from? y/n\n") + " ")[0].lower()
domainLock = (domainLock == "y")
rootDomain = getDomain(url)

domains = {}
page = Page(url)
pages.write(page)
links = nx.DiGraph()
history = []

window = tk.Tk() # Create Tk object
window.configure(bg='black')
window.wm_attributes('-zoomed', 1)
image = ImageTk.PhotoImage(Image.new("RGB", (100, 100))) # Make placeholder image for the label
label = tk.Label(window, image=image)
label.pack() # Add to the window

def refresh():
    # Whenever you update the window, do this to make the window reflect these changes
    window.update_idletasks()
    window.update()

refresh()

dpi = 60
inchWidth = window.winfo_width() / dpi
inchHeight = window.winfo_height() / dpi

def draw():
    try:
        plt.clf()
        pos = nx.kamada_kawai_layout(links)
        nx.draw(links, with_labels=True, pos=pos)
        plt.gcf().set_size_inches(inchWidth, inchHeight)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=60)
        buf.seek(0)
        fig = Image.open(buf).copy()
        buf.close()
        return fig
        # https://stackoverflow.com/a/3482156/
        #draw = ImageDraw.Draw(fig)
        #draw.text((0, 0), text, (255,255,255))
    except Exception as e:
        raise e

def drawGraph(text):
    img = draw()
    image = ImageTk.PhotoImage(img.copy())
    label.configure(image=image)
    label.image = image # Tkinter weirdness means this is how you do it
    refresh()

def add_edge(f, t):
    links.add_edge(f, t)

def stop(x=None):
    global running
    running = False
    window.quit()

window.protocol("WM_DELETE_WINDOW", stop)

window.bind("<Escape>", stop)

try:
    while running:
        page = pages.read()
        pages.remove()
        history.append(page.url)
        print(f"Checking links of {page.url}")
        try:
            assert page.hyperlinks
        except Exception as e:
            print(f"{page.url} was invalid. Reason: {e}")
            continue
        for link in page.hyperlinks:
            if not running:
                break
            try:
                newPage = Page(link)
                add_edge(page.url, link)
                if newPage.url in history or link in history:
                    print(f"Already discovered {link}")
                else:
                    print(f"Discovered link: {link}")
                    pages.write(newPage)
                    history.append(link)
            except Exception as e:
                if e == KeyboardInterrupt:
                    stop()
                    break
                print(f"Invalid link: {link}")
                raise e
                continue
        drawGraph(page.url)
except Exception as e:
    if e == IndexError:
        pass
    stop()

window.destroy()

fname = f"{dorb}-{url}-{len(links)}".replace("/", "-")
if not input("Save graph to json file? (y/n)\n")[0].lower() == "n":
    with open(f"{fname}.json", "w") as file:
        data = nx.node_link_data(links)
        json.dump(data, file, indent=4)
        print(f"Graph output written to {fname}")

if not input("Save graph as PNG file? (y/n)\n")[0].lower() == "n":
    img = draw()
    img.save(f"{fname}.png")