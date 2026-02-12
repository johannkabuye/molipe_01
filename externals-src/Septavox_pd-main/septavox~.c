#include <stdint.h>
#include "m_pd.h"  
#include "audio.h"
#include "oscillator.h"
#include "pp6.h"
#include "wave_synth.h"
#include "mode_adsr.h"
#include "mode_octave_arp.h"
#include "mode_simple_poly.h"
#include "mode_mega_wave.h"
#include "mode_octave_cascade.h"
#include "mode_slicer.h"
#include "mode_slider.h"

static t_class *septavox_tilde_class;

typedef struct _septavox_tilde {  
    t_object  x_obj; 
    uint8_t mode;
    t_outlet *out;

    // pp6 is the main data structure storing the state of the instrument.
    // In the original program, which runs on a microcontroller, all of 
    // the mode_ files contained tons of static variables.
    // So the quick and dirty thing to do is stuff all those in pp6 since it 
    // is already getting passed around. 
    pocket_piano pp6; 

} t_septavox_tilde;  

void septavox_tilde_bang(t_septavox_tilde *x) {
}

void septavox_tilde_notein(t_septavox_tilde *x, t_floatarg num, t_floatarg vel) {  
    //post("Received 'note' with values %f and %f", num, vel);

    if (vel <= 0) {
	    pp6_set_note_off(&(x->pp6), num);
	    pp6_dec_physical_notes_on(&(x->pp6));
    }
    else {
	    pp6_set_note_on(&(x->pp6),num);
	    pp6_inc_physical_notes_on(&(x->pp6));
    }
    pp6_allocate_voices(&(x->pp6));
}  

void septavox_tilde_freq0(t_septavox_tilde *x, t_floatarg freq) {  
//    x->pp6.freqs[0] = freq;
}

void septavox_tilde_waveform(t_septavox_tilde *x, t_floatarg num) { 
    uint8_t tmp;
    tmp = (uint8_t)num;
    if (tmp <= 0) tmp = 0;
    if (tmp >= 6) tmp = 0;
    x->pp6.aux_button_count = tmp;
}

void septavox_tilde_mode(t_septavox_tilde *x, t_floatarg num) { 
    uint8_t tmp;
    tmp = (uint8_t)num;
    if (tmp <= 0) tmp = 0;
    if (tmp >= 6) tmp = 6;
    x->mode = tmp;
}

void septavox_tilde_knob1(t_septavox_tilde *x, t_floatarg k) {  
    x->pp6.knob[0] = k;
}

void septavox_tilde_knob2(t_septavox_tilde *x, t_floatarg k) {  
    x->pp6.knob[1] = k;
}

void septavox_tilde_knob3(t_septavox_tilde *x, t_floatarg k) {  
    x->pp6.knob[2] = k;
}

void *septavox_tilde_new(void) {  
    t_septavox_tilde *x = (t_septavox_tilde *)pd_new(septavox_tilde_class);  

    x->out = outlet_new(&x->x_obj, &s_signal);

    pp6_init(&(x->pp6));
    wave_synth_init(&(x->pp6));
    mode_adsr_init(&(x->pp6));
    mode_octave_arp_init(&(x->pp6));
    mode_simple_poly_init(&(x->pp6));
    mode_mega_wave_init(&(x->pp6));
    mode_octave_cascade_init(&(x->pp6));
    mode_slicer_init(&(x->pp6));
    mode_slider_init(&(x->pp6));
    
    x->mode = 0;
    
    return (void *)x;  
}  

t_int *septavox_tilde_perform(t_int *w) {
    t_septavox_tilde *x = (t_septavox_tilde *)(w[1]);
    t_sample *out = (t_sample *)(w[2]);
    int n = (int)(w[3]);

    while (n--) {
        // *out++ = wave_synth_process(&(x->pp6));
        if (x->mode == 0) *out++ = mode_simple_poly_sample_process(&(x->pp6));
        if (x->mode == 1) *out++ = mode_slider_sample_process(&(x->pp6));
        if (x->mode == 2) *out++ = mode_octave_arp_sample_process(&(x->pp6));
        if (x->mode == 3) *out++ = mode_adsr_sample_process(&(x->pp6));
        if (x->mode == 4) *out++ = mode_octave_cascade_sample_process(&(x->pp6));
        if (x->mode == 5) *out++ = mode_slicer_sample_process(&(x->pp6));
        if (x->mode == 6) *out++ = mode_mega_wave_sample_process(&(x->pp6));
    }
    return (w + 4);
}

void septavox_tilde_dsp(t_septavox_tilde *x, t_signal **sp) {
    dsp_add(septavox_tilde_perform, 3, x, sp[0]->s_vec, sp[0]->s_n);
}

void septavox_tilde_setup(void) {  
    septavox_tilde_class = class_new(gensym("septavox~"),  
        (t_newmethod)septavox_tilde_new,  
        0, sizeof(t_septavox_tilde),  
        CLASS_DEFAULT, 0);  
    class_addbang(septavox_tilde_class, septavox_tilde_bang);  
    class_addmethod(septavox_tilde_class, (t_method)septavox_tilde_notein, gensym("notein"), A_DEFFLOAT, A_DEFFLOAT, 0);  
    class_addmethod(septavox_tilde_class, (t_method)septavox_tilde_waveform, gensym("waveform"), A_DEFFLOAT, 0);  
    class_addmethod(septavox_tilde_class, (t_method)septavox_tilde_mode, gensym("mode"), A_DEFFLOAT, 0);  
    class_addmethod(septavox_tilde_class, (t_method)septavox_tilde_knob1, gensym("knob1"), A_DEFFLOAT, 0);  
    class_addmethod(septavox_tilde_class, (t_method)septavox_tilde_knob2, gensym("knob2"), A_DEFFLOAT, 0);  
    class_addmethod(septavox_tilde_class, (t_method)septavox_tilde_knob3, gensym("knob3"), A_DEFFLOAT, 0);  
    class_addmethod(septavox_tilde_class, (t_method)septavox_tilde_freq0, gensym("freq0"), A_DEFFLOAT, 0);  

    class_addmethod(septavox_tilde_class, (t_method)septavox_tilde_dsp, gensym("dsp"), A_CANT, 0);
}
