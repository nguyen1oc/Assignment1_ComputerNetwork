# **Network Application: Torrent Tracker and Peer**

## **Team Members:**
- Nguyen Thien Loc - 2252460
- Ly Trieu Uy - 2252889

## **Objective:**
Build a Simple Torrent-like Application (STA) with the protocols defined by each group,
using the TCP/IP protocol stack and must support multi-direction data transfering (MDDT).

## **APPLICATION DESCRIPTION:**
The application includes the two types of hosts: tracker and node.
• A centralized tracker keeps track of multiple nodes and stores what pieces of files.
• Through tracker protocol, a node informs the server as to what files are contained in its local
repository but does not actually transmit file data to the server.
• When a node requires a file that does not belong to its repository, a request is sent to the
tracker.
• MDDT: The client can download multiple files from multiple source nodes at once,
simultaneously.
 This requires the node code to be a multithreaded implementation.
## **How to Run:**
Open terminal and choose gitbash, create at least 2 ( 1 for tracker and 1 for peer)
On the tracker gitbash run:

```bash
  python3 tracker.py
```
On the peer gitbash run:

```bash
  python3 peer.py
```

### Prerequisites:
Make sure you have Python 3.x installed on your system. You can check the Python version by running:

```bash
 python --version
```

And install all the library that we have imported in the source code
```bash
 pip install <library>
```
