#!/bin/bash
sleep 2
/usr/bin/jackd -d alsa -d hw:3 -r 44100 -p 128 -n 2 &
sleep 2
/usr/bin/pd -jack -alsamidi -midiindev 1 -midioutdev 1 /home/johann/001/main.pd &
sleep 3 
/usr/bin/aconnect 24:1 128:0 
/usr/bin/aconnect 128:1 24:1 
sleep infinity
