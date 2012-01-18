#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Perform the simulation of the transmission of PSK symbols through an
awgn channel."""

import numpy as np
import math

from matplotlib import pyplot as plt

# # Installed with pip
# # See http://www.doughellmann.com/articles/pythonmagazine/features/commandlineapp/index.html
# from commandlineapp import CommandLineApp

from util.conversion import dB2Linear
from util import misc
import comm.modulators as mod
from simulations import SimulationResults, Result, SimulationRunner2  # , SimulationParameters

#from cli.configfileparser import CaseSensitiveConfigParser
from configobj import ConfigObj


class SimplePskSimulationRunner(SimulationRunner2):
    """Implements a simulation runner for a transmission with a PSK
    modulation through an AWGN channel.

    In order to implement a simulation runner, 3 steps are required:
    - The simulation parameters must be added to the self.params variable
    - The _run_simulation funtion must be implemented. It must receive a
      single SimulationParameters object which contains the simulation
      parameters.
    - The _keep_going may be optionally implemented.
    """
    def __init__(self, rep_Max):
        """
        """
        SimulationRunner2.__init__(self, rep_Max)

        SNR = np.array([5, 10])
        M = 4
        NSymbs = 100
        self.modulator = mod.PSK(M)

        # We can add anything to the simulation parameters. Note that most
        # of these parameters will be used in the _run_simulation function
        # and we could put them there, but putting the parameters here
        # makes thinks more modular.
        self.params.add("description", "Parameters for the simulation of a {0}-PSK transmission through an AWGN channel ".format(M))
        self.params.add("SNR", SNR)
        self.params.add("M", M)         # Modulation cardinality
        self.params.add("NSymbs", NSymbs)  # Number of symbols that will be
                                           # transmitted in the _run_simulation
                                           # function

        # Unpack the SNR parameter
        self.params.set_unpack_parameter("SNR")

        # We will stop when the number of bit errors is greater than
        # max_bit_errors
        self.max_bit_errors = 5000

        # Message Exibited in the progressbar. Set to None to disable the
        # progressbar
        self.progressbar_message = "{M}-PSK Simulation - SNR: {SNR}"

    def _run_simulation(self, current_parameters):
        # To make sure that this function does not modify the object state,
        # we sobrescibe self to None.
        #self = None

        # xxxxx Input parameters (set in the constructor) xxxxxxxxxxxxxxxxx
        NSymbs = current_parameters["NSymbs"]
        M = current_parameters["M"]
        SNR = current_parameters["SNR"]
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Input Data xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        inputData = np.random.randint(0, M, NSymbs)
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Modulate input data xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        modulatedData = self.modulator.modulate(inputData)
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Pass through the channel xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        noiseVar = 1 / dB2Linear(SNR)
        noise = ((np.random.randn(NSymbs) + 1j * np.random.randn(NSymbs)) *
                 math.sqrt(noiseVar / 2))
        receivedData = modulatedData + noise
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Demodulate received data xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        demodulatedData = self.modulator.demodulate(receivedData)
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Calculates the symbol and bit error rates xxxxxxxxxxxxxxxxx
        symbolErrors = sum(inputData != demodulatedData)
        aux = misc.xor(inputData, demodulatedData)
        # Count the number of bits in aux
        bitErrors = sum(misc.bitCount(aux))
        numSymbols = inputData.size
        numBits = inputData.size * mod.level2bits(M)
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # xxxxx Return the simulation results xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        symbolErrorsResult = Result.create(
            "symbol_errors", Result.SUMTYPE, symbolErrors)

        numSymbolsResult = Result.create(
            "num_symbols", Result.SUMTYPE, numSymbols)

        bitErrorsResult = Result.create("bit_errors", Result.SUMTYPE, bitErrors)

        numBitsResult = Result.create("num_bits", Result.SUMTYPE, numBits)

        berResult = Result.create("ber", Result.RATIOTYPE, bitErrors, numBits)

        serResult = Result.create(
            "ser", Result.RATIOTYPE, symbolErrors, numSymbols)

        simResults = SimulationResults()
        simResults.add_result(symbolErrorsResult)
        simResults.add_result(numSymbolsResult)
        simResults.add_result(bitErrorsResult)
        simResults.add_result(numBitsResult)
        simResults.add_result(berResult)
        simResults.add_result(serResult)

        return simResults

    def _keep_going(self, simulation_results):
        # Return true as long as cumulated_bit_errors is lower then
        # max_bit_errors
        cumulated_bit_errors = simulation_results['bit_errors'][-1].get_result()
        return cumulated_bit_errors < self.max_bit_errors


class PskSimulationRunner(SimplePskSimulationRunner):
    """A more complete simulation runner for a transmission with a PSK
    modulation through an AWGN channel.

    Some features added to SimplePskSimulationRunner are configuration from
    a config file and plot of the results.
    """

    def __init__(self, config_file_name='psk_simulation_config.txt'):
        """
        """
        # Read the configuration file
        conf_file_parser = ConfigObj(config_file_name, list_values=True)

        # Pegue da linha de comando
        rep_max = int(conf_file_parser['Simulation']['rep_max'])
        M = int(conf_file_parser['Simulation']['M'])
        NSymbs = int(conf_file_parser['Simulation']['NSymbs'])
        SNR = conf_file_parser['Simulation']['SNR']
        SNR = [int(i) for i in SNR]
        max_bit_errors = int(conf_file_parser['Simulation']['max_bit_errors'])

        SimplePskSimulationRunner.__init__(self, rep_max)
        self.params.add('M', M)
        self.params.add('NSymbs', NSymbs)
        self.params.add('SNR', SNR)
        self.max_bit_errors = max_bit_errors
        self.modulator = mod.PSK(M)

    def plot_results(self):
        """Plot the results from the simulation, as well as the
        theoretical results.
        """
        def get_result_value(index, param_name):
            """
            """
            return self.results[index][param_name][0].get_result()

        # xxxxx Concatenate the simulation results xxxxxxxxxxxxxxxxxxxxxxxx
        N_SNR_values = len(self.results)
        ber = np.zeros(N_SNR_values)
        ser = np.zeros(N_SNR_values)
        for i in range(0, N_SNR_values):
            ber[i] = get_result_value(i, 'ber')
            ser[i] = get_result_value(i, 'ser')
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

        # Get the SNR from the simulation parameters
        SNR = np.array(self.params['SNR'])

        # xxxxx Plot the results xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        f = plt.figure()
        line1 = plt.plot(SNR, ber, 'o', color='green', label='Simulated BER')
        line2 = plt.plot(SNR, ser, '^', color='blue', label='Simulated SER')

        # Calculates the Theoretical SER and BER
        psk = mod.PSK(self.params['M'])
        theoretical_ser = psk.calcTheoreticalSER(dB2Linear(SNR))
        theoretical_ber = psk.calcTheoreticalBER(dB2Linear(SNR))

        line3 = plt.plot(SNR, theoretical_ber, color='green', label='Theoretical BER')
        line4 = plt.plot(SNR, theoretical_ser, color='blue', label='Theoretical SER')
        # Not really necessary. Just to make flymake happy in emacs
        line1 + line2 + line3 + line4

        # Get the first axes (we only have one, since subplot was not used)
        ax = f.axes[0]
        # Uses the label property of each line as the legend, since I'm not
        # specifying the legend here
        ax.legend()
        ax.set_title('PSK Simulation')
        ax.set_xlabel('SNR')
        ax.set_yscale('log')
        ax.axis('tight')
        ax.grid(True)

        f.show()
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


def write_config_file_template():
    """Write a configuration file that can be used to run the simulate
    function of a PskSimulationRunner object.
    """
    # See http://www.voidspace.org.uk/python/configobj.html#getting-started
    config_file_name = "psk_simulation_config.txt"
    configobj = ConfigObj(config_file_name)
    configobj.clear()
    configobj.initial_comment = ["Simulation Parameters"]

    # xxxxx Creates a section for the simulation parameters xxxxxxxxxxxxxxx
    configobj['Simulation'] = {}

    # xxxxx Simulation parameters xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    configobj['Simulation']['SNR'] = range(0, 19, 3)
    configobj['Simulation']['M'] = 4
    configobj['Simulation']['NSymbs'] = 5000
    configobj['Simulation']['rep_max'] = 20000
    configobj['Simulation']['max_bit_errors'] = 200

    # xxxxx Comments for each simulation parameters xxxxxxxxxxxxxxxxxxxxxxx
    # Get the simulation section
    s = configobj['Simulation']
    # All comments are lists of lines. We just need to append new lines
    s.comments['SNR'].extend(['', "SNR Values"])
    s.comments['M'].extend(['', "Modulation Cardinality"])
    s.comments['NSymbs'].extend(['', "Number of Symbols transmitted in each iteration"])
    s.comments['rep_max'].extend(['', "Maximum Number of iterations (Simulation stops after rep_max or", "max_bit_errors is reached)"])
    s.comments['max_bit_errors'].extend(['', "Maximum Number of bit Errors (Simulation stops after rep_max or", "max_bit_errors is reached)"])

    configobj.write()


# xxxxxxxxxx MAIN xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
if __name__ == '__main__':
    # UNCOMMENT THE LINE BELOW to create the configuration file. After
    # that, comment the line again and tweak the configuration file.
    #
    # write_config_file_template()

    psk_runner = PskSimulationRunner()
    psk_runner.simulate()

    print "Elapsed Time: {0}".format(psk_runner.elapsed_time)
    print "Iterations Executed: {0}".format(psk_runner.runned_reps)

    psk_runner.plot_results()
