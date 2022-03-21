#!/usr/bin/env python
#
# HF radar receiver
#
# The synchronization is done using a reference 1 PPS and 10 MHz signal.
# We assume that the code has a certain cycle length after it repeats, thus
# offering a logical place to synchronize to. The user gives the starting time
# in unix time and specifies the repeat time of the code. The receiver will then
# start sampling at the beginning of the next cycle.
#
# Tune to a certain frequency and store data as files of a certain length.
# Use a high over-the-wire sample rate and perform additional integration
# and decimation in single precision floating point format to achieve
# higher dynamic range, often needed for continuous radar.
#
# (c) 2013 Juha Vierinen
# 
from __future__ import division   #Libreria para obtener correctas divisiones
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import blks2
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from optparse import OptionParser 
from gnuradio.gr import firdes
from gnuradio import analog  # Libreria para modulacion generador de funciones analogicas



import sys, time, os, math, re, calendar, glob

import sampler_util
import filesink2
import stuffr
import numpy
import shutil

class beacon_receiver:

    def __init__(self,op):
        self.op = op  # Libreria OptParse[ se ingresan varias variables en una 
                      # sola linea en este atributo]:

    def start(self):

        u = uhd.usrp_source(
            device_addr="addr=%s,recv_buff_size=100000000"%(op.ip),
            stream_args=uhd.stream_args(
                cpu_format="fc32",
                channels=range(2),
                ),
            )

        u.set_subdev_spec(op.subdev) 
        #  u.set_subdev_spec(op.subdev[1],0)
        u.set_samp_rate(op.sample_rate)

        #u.set_center_freq(op.centerfreq[0], 0)
        #u.set_center_freq(op.centerfreq[1], 1)
        middle_frequency = (op.centerfreq[0]+op.centerfreq[1])/2
        desviations_frequencies= self.var_freq(3,op.centerfreq[0],op.centerfreq[1]) # Cantidad de pares de frecuencias 3 
        print "DESVIACIONES:",desviations_frequencies
        #deviation_frequency = abs((op.centerfreq[0]-op.centerfreq[1])/2)  # aqui se coloca el facto de correcion en frecuencia
        u.set_center_freq(middle_frequency, 0)
        u.set_center_freq(middle_frequency, 1)

        u.set_gain(op.gain,0)
        u.set_gain(op.gain,1)
        # 26200000.01043081283569335937500
        print "Actual center freq %1.2f Hz %1.2f"%(u.get_center_freq(0),u.get_center_freq(1))
        print "Middle and deviation freq %1.2f Hz %1.2f"%(middle_frequency,desviations_frequencies[0])
        ######### CLOCK SOURCE #########

        if op.clocksource != "none":
            u.set_clock_source(op.clocksource, 0)
            u.set_time_source(op.clocksource, 0)
	    print(u.get_mboard_sensor("ref_locked"))
        if op.clocksource == "gpsdo":
            print u.get_mboard_sensor("gps_time")
            print u.get_mboard_sensor("gps_locked")
            print "MOSTRANDO GPS-DO"   #GPS - DO

        ##############################

        fg = gr.top_block()
        print "Desviacion [0]: ",desviations_frequencies[0]
        print "Desviacion [1]: ",desviations_frequencies[1]
        print "Desviacion [2]: ",desviations_frequencies[2]
        ############################## FRECUENCIA BASE ##############################
    	signal_minus_dev_freq_0 = analog.sig_source_c(op.sample_rate, analog.GR_SIN_WAVE, +1.0*desviations_frequencies[0], 1, 0)
    	signal_plus_dev_freq_0 =  analog.sig_source_c(op.sample_rate, analog.GR_SIN_WAVE, -1.0*desviations_frequencies[0], 1, 0)
        
        ############################## FRECUENCIA Desviacion +3.329 ##############################
        signal_minus_dev_freq_1 = analog.sig_source_c(op.sample_rate, analog.GR_SIN_WAVE, +1.0*desviations_frequencies[1], 1, 0)
    	signal_plus_dev_freq_1 =  analog.sig_source_c(op.sample_rate, analog.GR_SIN_WAVE, -1.0*desviations_frequencies[1], 1, 0)
    	
        ############################## FRECUENCIA Desviacion -3.329 ##############################
        signal_minus_dev_freq_2 = analog.sig_source_c(op.sample_rate, analog.GR_SIN_WAVE, +1.0*desviations_frequencies[2], 1, 0)
    	signal_plus_dev_freq_2 =  analog.sig_source_c(op.sample_rate, analog.GR_SIN_WAVE, -1.0*desviations_frequencies[2], 1, 0) 
        
        ####### MEZCLADOR 3.18 +- freq base CH0 #######
        mixer0 = gr.multiply_vcc(1)
    	mixer1 = gr.multiply_vcc(1)
        ####### MEZCLADOR 3.18 +- freq base CH1#######
    	mixer2 = gr.multiply_vcc(1)
    	mixer3 = gr.multiply_vcc(1)
        ####### MEZCLADOR 3.18 +- freq base (+3.329) CH0#######
        mixer4 = gr.multiply_vcc(1)
        mixer5 = gr.multiply_vcc(1)
        ####### MEZCLADOR 3.18 +- freq base (+3.329) CH1#######
        mixer6 = gr.multiply_vcc(1)
        mixer7 = gr.multiply_vcc(1)
        ####### MEZCLADOR 3.18 +- freq base (-3.329) CH0#######
        mixer8 = gr.multiply_vcc(1)
        mixer9 = gr.multiply_vcc(1)
        ####### MEZCLADOR 3.18 +- freq base (-3.329) CH1#######
        mixer10 = gr.multiply_vcc(1)
        mixer11 = gr.multiply_vcc(1)


        ###########################################
    	taps_low_pass_filter = firdes.low_pass(1, op.sample_rate, 50e3, 20e3, firdes.WIN_HAMMING, 6.76)
    	#my_taps = firdes.low_pass(1, samp_rate, 0.2e6, 0.1e6, firdes.WIN_HAMMING, 6.76)
    	print "taps_low_pass_filter 200e3:",type(taps_low_pass_filter)
    	       
    	#print(taps_low_pass_filter)

    	self.low_pass_filter_0 = gr.fir_filter_ccf(20, taps_low_pass_filter)
    	self.low_pass_filter_1 = gr.fir_filter_ccf(20, taps_low_pass_filter)
    	self.low_pass_filter_2 = gr.fir_filter_ccf(20, taps_low_pass_filter)
    	self.low_pass_filter_3 = gr.fir_filter_ccf(20, taps_low_pass_filter)
        self.low_pass_filter_4 = gr.fir_filter_ccf(20, taps_low_pass_filter)
        self.low_pass_filter_5 = gr.fir_filter_ccf(20, taps_low_pass_filter)
        self.low_pass_filter_6 = gr.fir_filter_ccf(20, taps_low_pass_filter)
        self.low_pass_filter_7 = gr.fir_filter_ccf(20, taps_low_pass_filter)
        self.low_pass_filter_8 = gr.fir_filter_ccf(20, taps_low_pass_filter)
        self.low_pass_filter_9 = gr.fir_filter_ccf(20, taps_low_pass_filter)
        self.low_pass_filter_10 = gr.fir_filter_ccf(20, taps_low_pass_filter)
        self.low_pass_filter_11 = gr.fir_filter_ccf(20, taps_low_pass_filter)


#    	self.blks2_rational_resampler_0 = blks2.rational_resampler_ccc(interpolation=1, decimation=2, taps=None, fractional_bw=None)
#    	self.blks2_rational_resampler_1 = blks2.rational_resampler_ccc(interpolation=1, decimation=2, taps=None, fractional_bw=None)
#    	self.blks2_rational_resampler_2 = blks2.rational_resampler_ccc(interpolation=1, decimation=2, taps=None, fractional_bw=None)
#    	self.blks2_rational_resampler_3 = blks2.rational_resampler_ccc(interpolation=1, decimation=2, taps=None, fractional_bw=None)
#	    lpf02 = gr.integrate_cc(2)
#       lpf12 = gr.integrate_cc(2)
#       lpf22 = gr.integrate_cc(2)device_addr
#       lpf32 = gr.integrate_cc(2)

        """ Detecting current DOY """
        DOY=time.strftime("%Y%j", time.gmtime(time.time()-5*3600))

        dir_name = "%s/d%s"%(op.outputdir,DOY)

        #If the folder exists add the current hour and minute to "dir_name"
        if os.path.exists(dir_name):
            HHMM=time.strftime("%H%M", time.gmtime(time.time()-5*3600))
            dir_name = "%s/d%s_%s"%(op.outputdir,DOY,HHMM)

        rawdata_parent_folder = op.outputdir
	self.check_rawdata_number_of_file(rawdata_parent_folder)
        self.check_rawdata_end_flag(rawdata_parent_folder)

        self.create_structure(dir_name)

        # store settings in config file
        sampler_util.write_metadata(dirn=dir_name,
                                    sample_rate=op.sample_rate/(op.dec*op.dec0),
                                    center_frequencies=numpy.array(op.centerfreq))

        filesink_0 = filesink2.filesink("%s/0"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_1 = filesink2.filesink("%s/1"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_2 = filesink2.filesink("%s/2"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_3 = filesink2.filesink("%s/3"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_4 = filesink2.filesink("%s/4"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_5 = filesink2.filesink("%s/5"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_6 = filesink2.filesink("%s/6"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_7 = filesink2.filesink("%s/7"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_8 = filesink2.filesink("%s/8"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_9 = filesink2.filesink("%s/9"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_10 = filesink2.filesink("%s/10"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))
        filesink_11 = filesink2.filesink("%s/11"%(dir_name), gr.sizeof_gr_complex, int(op.filesize))



        filesink_0.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_1.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_2.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_3.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_4.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_5.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_6.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_7.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_8.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_9.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_10.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))
        filesink_11.set_samplerate(int(op.sample_rate/(op.dec*op.dec0)))

        next_time = sampler_util.find_next(op.start_time, per=op.rep)
        print "Starting at ",next_time
        print "Starting at ",stuffr.unix2datestr(next_time)
        u.set_start_time(uhd.time_spec(next_time+op.clockoffset/1e6))
        ## filesink.set_launchtime(int(next_time))
        #fg.connect((u,0), (lpf0,0), (filesink0,0))
        #fg.connect((u,1), (lpf1,0), (filesink1,0))
        
        ##################### FREQs BASE #################### 
        ################## CH0 - DESV base ##################
                        ########## 2.72 MHz #########
        fg.connect((u,0), (mixer0,0))
        fg.connect((signal_minus_dev_freq_0, 0), (mixer0, 1))
        fg.connect((mixer0,0), (self.low_pass_filter_0,0))
        fg.connect((self.low_pass_filter_0,0), (filesink_0,0))

                        ########## 3.64 MHz #########
        fg.connect((u,0), (mixer1,0))
        fg.connect((signal_plus_dev_freq_0, 0), (mixer1, 1))
        fg.connect((mixer1,0), (self.low_pass_filter_1,0))
        fg.connect((self.low_pass_filter_1,0), (filesink_1,0))

        ################## CH1 - DESV base ##################
                        ########## 2.72 MHz #########
        fg.connect((u,1), (mixer2,0))
        fg.connect((signal_minus_dev_freq_0, 0), (mixer2, 1))
        fg.connect((mixer2,0), (self.low_pass_filter_2,0))
        fg.connect((self.low_pass_filter_2,0), (filesink_2,0))

                        ########## 3.64 MHz #########
        fg.connect((u,1), (mixer3,0))
        fg.connect((signal_plus_dev_freq_0, 0), (mixer3, 1))
        fg.connect((mixer3,0), (self.low_pass_filter_3,0))
        fg.connect((self.low_pass_filter_3,0), (filesink_3,0))

        ##################### FREQ +alejadas ################
        ################## CH0 - DESV base + 3.329 ##########
                        ########## 2.72 MHz #########
        fg.connect((u,0), (mixer4,0))
        fg.connect((signal_minus_dev_freq_1, 0), (mixer4, 1))
        fg.connect((mixer4,0), (self.low_pass_filter_4,0))
        fg.connect((self.low_pass_filter_4,0), (filesink_4,0))

                        ########## 3.64 MHz #########
        fg.connect((u,0), (mixer5,0))
        fg.connect((signal_plus_dev_freq_1, 0), (mixer5, 1))
        fg.connect((mixer5,0), (self.low_pass_filter_5,0))
        fg.connect((self.low_pass_filter_5,0), (filesink_5,0))

        ################# CH1 - desv base +3.329 ###########
        fg.connect((u,1), (mixer6,0))
        fg.connect((signal_minus_dev_freq_1, 0), (mixer6, 1))
        fg.connect((mixer6,0), (self.low_pass_filter_6,0))
        fg.connect((self.low_pass_filter_6,0), (filesink_6,0))

        fg.connect((u,1), (mixer7,0))
        fg.connect((signal_plus_dev_freq_1, 0), (mixer7, 1))
        fg.connect((mixer7,0), (self.low_pass_filter_7,0))
        fg.connect((self.low_pass_filter_7,0), (filesink_7,0))


        ##################### FREQ +cercanas #################
        ################## CH0 - DESV base - 3.329 ##########
        fg.connect((u,0), (mixer8,0))
        fg.connect((signal_minus_dev_freq_2, 0), (mixer8, 1))
        fg.connect((mixer8,0), (self.low_pass_filter_8,0))
        fg.connect((self.low_pass_filter_8,0), (filesink_8,0))


        fg.connect((u,0), (mixer9,0))
        fg.connect((signal_plus_dev_freq_2, 0), (mixer9, 1))
        fg.connect((mixer9,0), (self.low_pass_filter_9,0))
        fg.connect((self.low_pass_filter_9,0), (filesink_9,0))

        ################# CH1 - desv base +3.329 ###########
        fg.connect((u,1), (mixer10,0))
        fg.connect((signal_minus_dev_freq_2, 0), (mixer10, 1))
        fg.connect((mixer10,0), (self.low_pass_filter_10,0))
        fg.connect((self.low_pass_filter_10,0), (filesink_10,0))

        fg.connect((u,1), (mixer11,0))
        fg.connect((signal_plus_dev_freq_2, 0), (mixer11, 1))
        fg.connect((mixer11,0), (self.low_pass_filter_11,0))
        fg.connect((self.low_pass_filter_11,0), (filesink_11,0))


        tt = time.time()
        while tt-math.floor(tt) < 0.2 or tt-math.floor(tt) > 0.3:
            tt = time.time()
            time.sleep(0.01)

        if op.clocksource != "none":
            u.set_time_unknown_pps(uhd.time_spec(math.ceil(tt)+1.0))
        
        fg.start()

        
        while True:

	    tmp = u.get_mboard_sensor("ref_locked")
	    #print("Test",tmp,"TEST")
            if not(tmp.to_bool()):
                print 'NoLocked'
                fg.stop()
                exit(0)
	    print u.get_mboard_sensor("ref_locked")


	        #print op.runtime

            if op.runtime != -1:
                if time.time()-next_time > op.runtime:
                    print "PARADA"
                    fg.stop()
                    exit(0)
            if filesink_0.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_1.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_2.get_overflow() > 0:
                print "Overflow detected. Stopping\n"
                exit(0)
            if filesink_3.get_overflow() > 0:
                print "Overflow detected. Stopping\n"
                exit(0)
            if filesink_4.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_5.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_6.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_7.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_8.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_9.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_10.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)
            if filesink_11.get_overflow() > 0:
                print("Overflow detected. Stopping\n")
                exit(0)

            #print "Testing Bucle ..."

            """ Here add code for detection of a new day """


            """ checking the current DOY """
            NEW_DOY = time.strftime("%Y%j", time.gmtime(time.time()-5*3600))
            #NEW_DOY = time.strftime("%Y%j", time.gmtime(time.time()+18*3600-45*60))
                      

            if NEW_DOY != DOY:
                print "New DOY detected"

                #Create rawdata_end_flag to indicate that the rawdata adquisition of that day has finished
                #old_dir_name = "%s/d%s"%(op.outputdir,DOY)
                old_dir_name = dir_name
                self.create_rawdata_end_flag(old_dir_name)

                # Change to the new DOY folder
                DOY = NEW_DOY
                dir_name = "%s/d%s"%(op.outputdir,DOY)
                self.create_structure(dir_name)
                filesink_0.change_dirname("%s/0"%(dir_name))
                filesink_1.change_dirname("%s/1"%(dir_name))
                filesink_2.change_dirname("%s/2"%(dir_name))
                filesink_3.change_dirname("%s/3"%(dir_name))
                filesink_4.change_dirname("%s/4"%(dir_name))
                filesink_5.change_dirname("%s/5"%(dir_name))
                filesink_6.change_dirname("%s/6"%(dir_name))
                filesink_7.change_dirname("%s/7"%(dir_name))
                filesink_8.change_dirname("%s/8"%(dir_name))
                filesink_9.change_dirname("%s/9"%(dir_name))
                filesink_10.change_dirname("%s/10"%(dir_name))
                filesink_11.change_dirname("%s/11"%(dir_name))


                sampler_util.write_metadata(dirn=dir_name,
                                    sample_rate=op.sample_rate/(op.dec*op.dec0),
                                    center_frequencies=numpy.array(op.centerfreq))


            time.sleep(1)

    def var_freq(self,cantidad,f0,f1):
        paso = 100000000/pow(2,32)*143   # Variacion de 3.3294... Hz
        i = 0                            # Contador para frecuencias
        desv = []
        while(i<cantidad):
            FREQ =[f0+((-1)**i)*math.ceil(i/2)*paso,f1-((-1)**i)*math.ceil(i/2)*paso]
            desv.append((FREQ[1]-FREQ[0])/2)
            i+=1
            print FREQ
        return desv                       # Nuevas desviaciones con variacion de +- 3.329 ... Hz

    def create_structure(self, new_dir_name):

        os.system("mkdir -p %s"%(new_dir_name))
        os.system("mkdir -p %s/0"%(new_dir_name))
        os.system("mkdir -p %s/1"%(new_dir_name))
        os.system("mkdir -p %s/2"%(new_dir_name))
        os.system("mkdir -p %s/3"%(new_dir_name))
        os.system("mkdir -p %s/4"%(new_dir_name))
        os.system("mkdir -p %s/5"%(new_dir_name))
        os.system("mkdir -p %s/6"%(new_dir_name))
        os.system("mkdir -p %s/7"%(new_dir_name))
        os.system("mkdir -p %s/8"%(new_dir_name))
        os.system("mkdir -p %s/9"%(new_dir_name))
        os.system("mkdir -p %s/10"%(new_dir_name))
        os.system("mkdir -p %s/11"%(new_dir_name))

    #create rawdata end flag file
    def create_rawdata_end_flag(self, dir_name):

        os.system("touch %s/rawdata_end_flag"%(dir_name))


    def check_rawdata_end_flag(self, rawdata_parent_folder):
        #Verifica si la generacion de datos crudos finalizo con la creacion de un archivo
        dirns = []
        dirns = dirns + glob.glob("%s/d*"%(rawdata_parent_folder))
        dirns.sort()

        for tmp in dirns[-5:]:
            print "Checking if rawdata_end_flag exists in folder %s"%(tmp)
            if not os.path.isfile("%s/rawdata_end_flag"%(tmp)):
                print("Creating rawdata_end_flag")
                self.create_rawdata_end_flag(tmp)

    def check_rawdata_number_of_file(self,rawdata_parent_folder):
	#-1 borra lo anterior considera la lista de dias y evalua todo menos el ultimo
    # borra los archivos gdf de cada folder, empezando por los creados de forma creciente y menos el ultimo
	    dirns=[]
	    dirns = dirns + glob.glob("%s/d*"%(rawdata_parent_folder))
	    dirns.sort()

	    for tmp in dirns[:-1]:#antes estaba dirns[-3:]               #Solo analiza el folder 0 y 
	        number_gdf = glob.glob("%s/%s/*.gdf"%(tmp,0))
	        if number_gdf < 3:  #Porque solo cuando es menor que 3
		    dirns.remove(tmp)
		    shutil.rmtree(tmp)




if __name__ == '__main__':

    """
    Version 1.0.2.1_beta_ric

    Adquisition

    python ./hfrx2_ric_new.py -a 192.168.10.2 -r 2000000 -y 2 -d 10
    -b external -o /full_path/rawdata/ -e 11.5 -c 2.72e6,3.64e6

    """

    print "######### Ricardo NEWWW ###########"
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")

    parser.add_option("-a", "--address",
                      dest="ip",
                      type="string",
                      action="store",
                      default="192.168.10.2",#CAMBIAR IP
                      help="Device address (ip number).")

    parser.add_option("-r", "--samplerate", dest="sample_rate", type="int",action="store",
                      default=2000000,
                      help="Sample rate (default = 1 MHz).")

    parser.add_option("-t", "--rep", dest="rep", type="int",action="store", default=1,
                      help="Repetition time (default = 1 s)")

    parser.add_option("-d", "--dec", dest="dec", type="int",action="store", default=10,
                      help="Integrate and decimate by this factor (default = 10)")

    parser.add_option("-y", "--dec0", dest="dec0", type="int",action="store", default=2,
                      help="First decimator factor (default = 2)")

    parser.add_option("-z", "--filesize", dest="filesize", type="int",action="store",
                      help="File size (samples 1 second)")

    parser.add_option("-s", "--starttime", dest="start_time", type="int", action="store",
                      help="Start time (unix seconds)")

    parser.add_option("-f", "--runtime", dest="runtime", type="int", action="store", default=-1,
                      help="Number of seconds to run (seconds)")

    parser.add_option("-x", "--subdev", dest="subdev", type="string", action="store", default="A:A A:B",
                      help="RX subdevice spec (default=RX2)")

      ################################ NUEVAS FRECUENCIAS BASE ###########################################
    #parser.add_option("-c", "--centerfreq",dest="centerfreq", action="store", type="string",default="2.728271484375e6,3.643798828125e6",
    #                  help="Center frequency (default 2.4e9,2.4e9)")
    
    ################################## FRECUENCIAS BASE ORIGINALES #######################################
    parser.add_option("-c", "--centerfreq",dest="centerfreq", action="store", type="string",default="2.72216796875e6,3.64990234375e6",
                      help="Center frequency (default 2.4e9,2.4e9)")


    parser.add_option("-b", "--clocksource",dest="clocksource", action="store", type="string", default="external",
                      help="Clock source (default gpsdo)")

    parser.add_option("-o", "--outputdir",dest="outputdir", action="store", type="string", default="/media/igp-114/RAWDATA/",
                      help="Output destination (default hfrx-datestring)")

    parser.add_option("-g", "--gain",dest="gain", action="store", type="float", default=20.0,
                      help="Gain (default 20 dB)")

    parser.add_option("-e", "--clockoffset",dest="clockoffset", action="store", type="float", default=11.5,
                      help="Clock offset in microseconds (default 0.0 us).")

    (op, args) = parser.parse_args()

    op.recv_buff_size = 100000000
    op.send_buff_size = 100000

    if op.start_time == None:
        op.start_time = math.ceil(time.time())

    cf = op.centerfreq.split(",")
    op.centerfreq = [float(cf[0]),float(cf[1])]
    print op.centerfreq

    if op.filesize == None:
        op.filesize = op.sample_rate/(op.dec*op.dec0)

    s = beacon_receiver(op)
    s.start()
