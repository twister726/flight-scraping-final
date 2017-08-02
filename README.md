# flight-scraping-final

## Setup

First copy the folder to whichever computer to run the scraper on (e.g. AWS, Google Cloud server, etc)

- Install `python3`, `pip3`, `virtualenv`
- Run `virtualenv venv` followed by `source bin/activate` to create and enter a Python virtual environment for the scraper.
- Use [this](https://christopher.su/2015/selenium-chromedriver-ubuntu/) guide to install the following
    - Google Chrome browser
    - `xvfb ` (for running Chrome without a display)
    - Chromedriver (for running Chrome headlessly)
- Download PhantomJS browser from [here](http://phantomjs.org/download.html) and extract the compressed file somewhere on the computer.
- Add the `bin` folder in the folder previously extracted to the system `PATH` environment variable. On Linux you can add `export PATH=$PATH:/home/sourabh/phantomjs-2.1.1-linux-x86_64/bin` to your `.bashrc` file.
- Run `pip3 install -r requirements.txt` to install all required Python packages

## Algorithm

- We note all active planes (flying right now) of all Indian airlines, and add them to a check list which is maintained across iterations of the algorithm.
- Then we iterate over all the inactive planes in the check list - we save their most recent flight (only if it's domestic) and remove the plane from the check list.

To work on this code, you should familiarize yourself with the flightradar24 web interface, especially the
individual aircraft pages (`www.flightradar24.com/data/aircraft/<tail_number>`) and
airline pages (`www.flightradar24.com/data/aircraft/<airline_identifier>`), and also be comfortable with multithreading in Python.
