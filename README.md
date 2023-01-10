# GeoDoodle
## About
GeoDoodle is a graph paper-like doodle program. I really like doodling on graph paper, making cool repeating patterns so I decided to automate it. With it, you create cool patterns using various tools and features I've added. You can also load, save, or export your pattern. It is not, however, just a regular drawing program. All the lines are intended to line up with the dots, or other lines.

It has been my personal cutting edge project; I keep rewriting it whenever I learn new things. That's why there's old versions of them in here. They're old and gross, but I spent so much time on them its a shame to just delete them.

## Installation
It's written in modern Python using PyQt6 (never could get pyside to work for me). The Qt_Version is the current version.
```
git clone https://github.com/smartycope/GeoDoodle.git
cd GeoDoodle
pip install -r requirements.txt
```


## Brief History
I first wrote it in C++ on top of the freeglut API, because it was my first semester of college and I was excited about this cool idea that I had and I could actually do it. Freeglut was what my assignments that semester used, so I just hacked that code, not really knowing what I was doing. Someone really needs to write new assignments for that class.

I then came back to the project about a year later, after starting many other projects, and knowing way, way more. I also had discovered python, God's gift to programmers. I ended up scrapping the entire codebase, and rewriting the entire thing from scratch in python, and to get roughtly where I was before, took me about 4 hours. It was pretty cool. I then added a bunch more features and made everything a lot nicer (pygame is an excellent API), including adding menus and options and a better repeating system. I eventually got stymied by the GUI's though. At that point I hadn't really done much with GUI's, and tried using pygame-gui, which isn't a bad API, it's just really not meant for what I wanted, and ended up writing huge, very nasty wrappers around their classes and it just wasn't worth it.

A couple months later, I had the idea to use Qt It was something I'd wanted to learn for a while, but I never really had a project suited to it, until I realized this was perfect. Turns out, Qt is freaking FANTASTIC. I love it. There's a reason it's so popular. It definitely takes getting used to, but it's all very clean, and QtCreator is absolutely fantastic. I hate having to manually position UI items in code. Using Qt allowed me to expand even further, and add more features far more intuitively.
