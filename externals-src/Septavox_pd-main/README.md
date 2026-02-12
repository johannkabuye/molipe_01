# septavox_pd

This is a Pure Data (Pd) object that encapsulates the Critter & Guitari Septavox. The Septavox is an electric wave organ with selectable waveforms and playing modes. See the help patch for more info. The object uses the same code as the original instrument so it should sound and behave pretty much the same. It doesn't require a lot of processing so you can run many instances of the object without problems. In the Organelle folder are a couple Septavox patches for the Organelle. The patch Septavox Quad has four instances of septavox~ that are detuned slightly for a chorus effect.

The object takes MIDI note style pairs, a number to select mode and waveform, and 3 control knobs. The first knob is always tuning. The second two depend on the mode:

| Mode                | Knob 1     | Knob 2     |
|---------------------|------------|------------|
| 0 - Vibrato         | Rate       | Depth      |
| 1 - Slide           | Glide Time | Amount     |
| 2 - Two-Octave Arp  | Rate       | Envelope   |
| 3 - Swell           | Attack     | Decay      |
| 4 - Octave Cascade  | Rate       | Envelope   |
| 5 - Slicer          | Rate       | Pattern    |
| 6 - Pipe Glide      | Glide Time | Modulation |

Waveforms are:

| Waveform            |
|---------------------|
| 0 - Dirty Sine      |
| 1 - Sine            |
| 2 - Electric Organ  |
| 3 - Square          |
| 4 - Sawtooth        |
| 5 - Dirty Square    |
| 6 - Computer        |


