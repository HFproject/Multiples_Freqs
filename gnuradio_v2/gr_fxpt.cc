/* -*- c++ -*- */
/*
 * Copyright 2004 Free Software Foundation, Inc.
 *
 * This file is part of GNU Radio
 *
 * GNU Radio is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * GNU Radio is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GNU Radio; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gr_fxpt.h>

const float gr_fxpt::s_sine_table[1 << NBITS][2] = {
#include "sine_table.h"
};

const float gr_fxpt::PI = 3.14159265358979323846;
const float gr_fxpt::TWO_TO_THE_31 = 2147483648.0;
// se añadio estos dos utlimos
const double gr_fxpt::TWO_TO_THE_31_double = 2147483648.0;
const double gr_fxpt::PI_double = 3.1415926535897932384626433832;

