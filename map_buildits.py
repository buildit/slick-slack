# This code needs to be run in Jupytor!

import matplotlib.pyplot as plt
import seaborn as sns
import slickslack as sl
from IPython.display import Javascript

%matplotlib inline
%load_ext autoreload
%autoreload 2


users = sl.load_user_dict()
chans = sl.load_channels(includes=['buildit*', '*lbg*', '*sandbox*'])

msgs = sum([], [m for c in chans
            for m in c['messages']
            #if not m.get('is_intro') and not m.get('subtype')])
            if not m.get('is_intro') and not m.get('subtype')] )


buildit = filter(lambda c: c['channel_info']['name'] == "buildit",chans)

def is_buildit_user(uid):
    return uid in buildit[0]['channel_info']['members']


# Draw a pretty graph
import networkx as nx

g = nx.Graph()
for e in filter(lambda conn: is_buildit_user(conn['s']) and is_buildit_user(conn['t']), sl.iter_connections(msgs)):
    g.add_edge(users[e['s']], users[e['t']])

pos=nx.spring_layout(g)
plt.figure(1,figsize=(20,20))
nx.draw(g,pos,
        node_color='#A0CBE2',
        edge_color='#BB0000',
        node_size=60,
        font_size=10,
        width=1,
        edge_cmap=plt.cm.Blues,
        with_labels=True)
