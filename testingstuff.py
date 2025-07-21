import json, io
import networkx as nx
import matplotlib.pyplot as plt
from PIL import Image

with open("breadth-https:--james.chaosgb.co.uk-16.json", "r") as f:
    data = json.load(f)
    f.close()

links = nx.node_link_graph(data, directed=True)

nx.draw(links, with_labels=True)
buf = io.BytesIO()
plt.savefig(buf, format='png')
buf.seek(0)
fig = Image.open(buf).copy()
buf.close()
fig.show()
