/*
 * mode_slider.h
 *
 *  Created on: Jan 7, 2015
 *      Author: owen
 */

#ifndef MODE_SLIDER_H_
#define MODE_SLIDER_H_

#include "pp6.h"

void mode_slider_init (pocket_piano *pp6);

float mode_slider_sample_process (pocket_piano *pp6);

void mode_slider_stop_notes (pocket_piano *pp6);

#endif /* MODE_SLIDER_H_ */
