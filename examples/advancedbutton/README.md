### Advanced button

This example shows how you can add additional functionallity to the move hub button. 

It adds three new actions which you can use instead of the standard subscription to a button press:

- Click - a single quick up/down press
- Double click - a double up/down press, second click must occur within .5 secs of first one 
- Long press - a press and hold on the button for > .7 secs 

```python
from pylgbst.hub import MoveHub
from advancedbutton import AdvancedButton
import time


hub = MoveHub()
b = AdvancedButton(hub)


def clicked():
    print("button clicked")


def pressed():
    print("button pressed")


def doubleclicked():
    print("button double clicked")


b.click.subscribe(clicked)
b.double_click.subscribe(doubleclicked)
b.long_press.subscribe(pressed)

time.sleep(120)
```

You can alter the timings using the two constants `DOUBLE_CLICK_TIME` and `LONG_PRESS_TIME`
