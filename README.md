# JaegerBot
An IRC bot for the sce-na-telco team written as a simple project for me to learn and practice the python language.

## Current Karma Capabilities
* ++
* --
* rank
* score
* X versus Y
* top
* bottom
* suppression of disallowed names with autoresponse
* search 

## Weather Reports
* Current conditions
* +hourly for next 5 hours temperature and precipitation forecast
* +daily (or +forecast) for next 5 days high/low temperature and summary

~~~~
GipsyDanger: weather Raleigh
> Raleigh, NC, USA                   
>     \   /    | Clear               
>      .~.     | 86°F (feels 89°F)   
>  -- (   ) -- | No precipitation    
>      `~’     | ↓ 8mph winds        
>     /   \    | View 10.0 miles     
~~~~
~~~~
GipsyDanger: weather Raleigh +hourly
> Raleigh, NC, USA                   
>     \   /    | Clear                | 6:PM 86°F  + No precipitation  
>      .~.     | 86°F (feels 89°F)    | 7:PM 84°F  + Rain%[          ] 
>  -- (   ) -- | No precipitation     | 8:PM 81°F  + Rain%[▓▓░░░░░░░░] 
>      `~’     | ↓ 8mph winds         | 9:PM 80°F  + Rain%[▓░░░░░░░░░] 
>     /   \    | View 10.0 miles      |10:PM 78°F  + Rain%[          ] 
~~~~
~~~~
GipsyDanger: weather Raleigh +daily
> Raleigh, NC, USA                   
>     \   /    | Clear                | Sat (88°/74°) Drizzle until afternoon.
>      .~.     | 86°F (feels 89°F)    | Sun (88°/69°) Light rain starting in the evening.
>  -- (   ) -- | No precipitation     | Mon (88°/73°) Rain throughout the day.
>      `~’     | ↓ 8mph winds         | Tue (80°/72°) Rain until afternoon, starting again in the evening.
>     /   \    | View 10.0 miles      | Wed (81°/71°) Rain throughout the day.
~~~~

## Other Features
* botsnack random smile emoji response
* award stamps for karma levels
* dictionary lookup
	

## Planned features
* 'give' stamps
* in-channel operator controls
* moar+bettah stamps
* something else ... ?

## Dependencies
~~~~
sudo dnf install pip
pip install geocoder
~~~~