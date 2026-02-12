/* tape~ - Airwindows Tape saturation for Pure Data */
/* Based on Airwindows Tape by Chris Johnson */
/* Ported to Pd external */

#include "m_pd.h"
#include <math.h>
#define FLOAT double

// ========== TAPE SETTINGS ==========
#define INPUT_GAIN 1.0     // ← 0.5 = -6dB, 1.0 = unity, 2.0 = +6dB
#define HEAD_BUMP 0.05     // ← 0.0 = none, 0.1 = maximum bass bump
// ===================================


typedef struct _tape
{
    t_object x_obj;
    t_float x_f;
    
    FLOAT x_sr;
    
    // State variables for filters
    FLOAT iirMidRollerA;
    FLOAT iirMidRollerB;
    FLOAT iirHeadBumpA;
    FLOAT iirHeadBumpB;
    
    // Biquad state for head bump filter
    FLOAT biquadA[9];  // coefficients + state
    FLOAT biquadB[9];
    
    FLOAT lastSample;
    int flip;

} t_tape;


static t_class *tape_class;


// Spiral saturation - the heart of Tape
static inline FLOAT spiral_saturate(FLOAT input)
{
    // Clip to maximum for clean saturation
    if (input > 1.2533141373155) input = 1.2533141373155;
    if (input < -1.2533141373155) input = -1.2533141373155;
    
    // Spiral formula: sin(x*|x|)/|x|
    FLOAT absInput = fabs(input);
    if (absInput == 0.0) return 0.0;
    
    return sin(input * absInput) / absInput;
}


// ADClip soft limiting
static inline FLOAT adclip(FLOAT input, FLOAT *lastSample)
{
    FLOAT softness = 0.618033988749894848204586;  // Golden ratio
    
    if (*lastSample >= 0.99)
    {
        if (input < 0.99) *lastSample = ((0.99 * softness) + (input * (1.0 - softness)));
        else *lastSample = 0.99;
    }
    
    if (*lastSample <= -0.99)
    {
        if (input > -0.99) *lastSample = ((-0.99 * softness) + (input * (1.0 - softness)));
        else *lastSample = -0.99;
    }
    
    if (input > 0.99)
    {
        if (*lastSample < 0.99) input = ((0.99 * softness) + (*lastSample * (1.0 - softness)));
        else input = 0.99;
    }
    
    if (input < -0.99)
    {
        if (*lastSample > -0.99) input = ((-0.99 * softness) + (*lastSample * (1.0 - softness)));
        else input = -0.99;
    }
    
    *lastSample = input;
    return input;
}


static void *tape_new(void)
{
    t_tape *x = (t_tape *)pd_new(tape_class);
    outlet_new(&x->x_obj, &s_signal);
    
    x->x_f = 0;
    x->iirMidRollerA = 0.0;
    x->iirMidRollerB = 0.0;
    x->iirHeadBumpA = 0.0;
    x->iirHeadBumpB = 0.0;
    x->lastSample = 0.0;
    x->flip = 0;
    
    // Initialize biquad arrays
    int i;
    for (i = 0; i < 9; i++) {
        x->biquadA[i] = 0.0;
        x->biquadB[i] = 0.0;
    }
    
    return (x);
}


static t_int *tape_perform(t_int *w)
{
    t_tape *x = (t_tape *)(w[1]);
    t_float *in = (t_float *)(w[2]);
    t_float *out = (t_float *)(w[3]);
    int n = (int)(w[4]);
    
    FLOAT overallscale = x->x_sr / 44100.0;
    FLOAT softness = 0.618033988749894848204586;
    FLOAT RollAmount = (1.0 - softness) / overallscale;
    FLOAT HeadBumpFreq = 0.12 / overallscale;
    
    // Setup biquad for head bump (only needs to be done once, but doing per-block is fine)
    FLOAT biquadFreq = 0.0072 / overallscale;
    FLOAT biquadQ = 0.0009;
    FLOAT K = tan(M_PI * biquadFreq);
    FLOAT norm = 1.0 / (1.0 + K / biquadQ + K * K);
    FLOAT a0 = K / biquadQ * norm;
    FLOAT a1 = 0.0;
    FLOAT a2 = -a0;
    FLOAT b1 = 2.0 * (K * K - 1.0) * norm;
    FLOAT b2 = (1.0 - K / biquadQ + K * K) * norm;
    
    x->biquadA[2] = x->biquadB[2] = a0;
    x->biquadA[3] = x->biquadB[3] = a1;
    x->biquadA[4] = x->biquadB[4] = a2;
    x->biquadA[5] = x->biquadB[5] = b1;
    x->biquadA[6] = x->biquadB[6] = b2;
    
    while (n--)
    {
        FLOAT inputSample = *in++;
        FLOAT drySample = inputSample;
        
        // Apply input gain
        inputSample *= INPUT_GAIN;
        
        FLOAT HighsSample = 0.0;
        FLOAT tempSample;
        
        // Alternate between A and B filters for smoothness
        if (x->flip)
        {
            // High frequency roll-off
            x->iirMidRollerA = (x->iirMidRollerA * (1.0 - RollAmount)) + (inputSample * RollAmount);
            HighsSample = inputSample - x->iirMidRollerA;
            
            // Head bump resonance
            x->iirHeadBumpA += (inputSample * 0.05);
            x->iirHeadBumpA -= (x->iirHeadBumpA * x->iirHeadBumpA * x->iirHeadBumpA * HeadBumpFreq);
            x->iirHeadBumpA = sin(x->iirHeadBumpA);
            
            // Biquad filter on head bump
            tempSample = (x->iirHeadBumpA * x->biquadA[2]) + x->biquadA[7];
            x->biquadA[7] = (x->iirHeadBumpA * x->biquadA[3]) - (tempSample * x->biquadA[5]) + x->biquadA[8];
            x->biquadA[8] = (x->iirHeadBumpA * x->biquadA[4]) - (tempSample * x->biquadA[6]);
            x->iirHeadBumpA = tempSample;
            
            if (x->iirHeadBumpA > 1.0) x->iirHeadBumpA = 1.0;
            if (x->iirHeadBumpA < -1.0) x->iirHeadBumpA = -1.0;
            x->iirHeadBumpA = asin(x->iirHeadBumpA);
        }
        else
        {
            x->iirMidRollerB = (x->iirMidRollerB * (1.0 - RollAmount)) + (inputSample * RollAmount);
            HighsSample = inputSample - x->iirMidRollerB;
            
            x->iirHeadBumpB += (inputSample * 0.05);
            x->iirHeadBumpB -= (x->iirHeadBumpB * x->iirHeadBumpB * x->iirHeadBumpB * HeadBumpFreq);
            x->iirHeadBumpB = sin(x->iirHeadBumpB);
            
            tempSample = (x->iirHeadBumpB * x->biquadB[2]) + x->biquadB[7];
            x->biquadB[7] = (x->iirHeadBumpB * x->biquadB[3]) - (tempSample * x->biquadB[5]) + x->biquadB[8];
            x->biquadB[8] = (x->iirHeadBumpB * x->biquadB[4]) - (tempSample * x->biquadB[6]);
            x->iirHeadBumpB = tempSample;
            
            if (x->iirHeadBumpB > 1.0) x->iirHeadBumpB = 1.0;
            if (x->iirHeadBumpB < -1.0) x->iirHeadBumpB = -1.0;
            x->iirHeadBumpB = asin(x->iirHeadBumpB);
        }
        x->flip = !x->flip;
        
        // Apply high frequency softening
        FLOAT applySoften = fabs(HighsSample) * 1.57079633;
        if (applySoften > 1.57079633) applySoften = 1.57079633;
        applySoften = 1.0 - cos(applySoften);
        if (HighsSample > 0) inputSample -= applySoften;
        if (HighsSample < 0) inputSample += applySoften;
        
        // SPIRAL SATURATION - The magic!
        inputSample = spiral_saturate(inputSample);
        
        // Restrain head bump resonance
        FLOAT suppress = (1.0 - fabs(inputSample)) * 0.00013;
        if (x->iirHeadBumpA > suppress) x->iirHeadBumpA -= suppress;
        if (x->iirHeadBumpA < -suppress) x->iirHeadBumpA += suppress;
        if (x->iirHeadBumpB > suppress) x->iirHeadBumpB -= suppress;
        if (x->iirHeadBumpB < -suppress) x->iirHeadBumpB += suppress;
        
        // Add head bump
        inputSample += ((x->iirHeadBumpA + x->iirHeadBumpB) * HEAD_BUMP);
        
        // ADClip final limiting
        inputSample = adclip(inputSample, &x->lastSample);
        
        // Final hard clip
        if (inputSample > 0.99) inputSample = 0.99;
        if (inputSample < -0.99) inputSample = -0.99;
        
        *out++ = inputSample;
    }
    
    return (w+5);
}


static void tape_dsp(t_tape *x, t_signal **sp)
{
    x->x_sr = sp[0]->s_sr;
    dsp_add(tape_perform, 4, x, sp[0]->s_vec, sp[1]->s_vec, sp[0]->s_n);
}


void tape_tilde_setup(void)
{
    tape_class = class_new(gensym("tape~"),
        (t_newmethod)tape_new, 0, sizeof(t_tape), 0, 0);
    class_addmethod(tape_class, (t_method)tape_dsp, gensym("dsp"), A_CANT, 0);
    CLASS_MAINSIGNALIN(tape_class, t_tape, x_f);
}
