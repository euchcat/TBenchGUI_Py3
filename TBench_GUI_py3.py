#!/usr/bin/python3
# -*- coding: utf-8 -*-
# =====================================================================
# Auteur: LGU <adresse@provider.ch>
# GNU General Public License (GPL) 2016
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# =====================================================================

import os
import signal
import time
import serial
import codecs

from gi.repository import Gtk
import collections
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
# uncomment to select /GTK/GTKAgg/GTKCairo
# from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
# from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas

from matplotlib import pylab

pylab.hold(False)  # prévient du manque de mémoire (nettoyage)


# =====================================================================

class Arduino():
    comport = ''
    baud = 115200

    def __init__(self):
        self.ser = None

    def search(self):
        # Les ports peuvent changer, on recherche l'arduino (PLC)
        baud = Arduino.baud
        baseports = ['/dev/ttyUSB', '/dev/ttyACM']
        self.ser = None
        for baseport in baseports:
            if self.ser: break
            for i in range(0, 8):
                try:
                    port = baseport + str(i)
                    self.ser = serial.Serial(port, baud, timeout=0)
                    Arduino.comport = port
                    info = ("présent sur " + port)
                    time.sleep(0.8)
                    self.ser.flushInput()  # nettoyage buffer d'entrée
                    self.ser.close()
                    return info
                    break
                except:
                    pass

        if not self.ser:
            info = "impossible d'ouvrir un port série"
            return info
            # raise IOError("Couldn't open a serial port")
            # nettoyage buffer d'entrée
            # self.flush()
            # self.buffer = ''

    def open(self):
        # Ouverture du port com Arduino
        baud = Arduino.baud
        try:
            self.ser = serial.Serial(Arduino.comport, baud, timeout=0.1)
            # self.flush()    # nettoyage buffer d'entrée
        except:
            self.ser = None
            print("impossible d'ouvrir le port PLC")
            # raise IOError("Couldn't open arduino com port")
            pass
            # self.buffer = ''

    def close(self):
        self.ser.close()

    def flush(self):
        self.ser.flushInput()

    def readbyte(self):
        # Retourne le premier caractère recu dans le buffer serie.
        # r = self.ser.read(self.ser.inWaiting())
        r = self.ser.read(1)
        if not r:
            return "None"
        # return r[-1]
        return r

    def reading(self):
        # lit une ligne complète finissant par '\n' ou '\n\r'
        # on enlève ces caractères de fin de ligne pour notre appli.
        # in_msg = self.ser.readline().rstrip('\n\r')
        in_msg = self.ser.readline()
        if not in_msg:
            #return "Rien...\n\r"
            in_msg = codecs.encode("Rien...\n\r", "cp850")
        return in_msg

    def write(self, sval):
        # print("sending:", sval)    #DEBUG: passage de valeur correcte
        self.ser.write(sval.encode('ascii'))


# =====================================================================

class UI:
    # ====== Variables de la classe UI ========
    xn, yn = 0, 0

    # =========================================
    def __init__(self):
        # ### Initialise les datas###
        self.array_size = 10
        self.nbr_dots = 1
        # ###########################
        self.builder = Gtk.Builder()  # voir commentaires lignes 21-25
        # self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(os.getcwd(), 'TBench_GUI_gl3.ui'))
        self.window = self.builder.get_object('dialog1')
        self.aboutdialog = self.builder.get_object('aboutdialog1')
        self.assistant = self.builder.get_object('assistant1')
        self.textview = self.builder.get_object('textview1')
        self.textbuffer = self.builder.get_object('textbuffer1')
        self.bt_exit = self.builder.get_object('bt_exit')
        self.tbt_state0 = self.builder.get_object('tbt_state0')
        self.tbt_state1 = self.builder.get_object('tbt_state1')
        self.tbt_state2 = self.builder.get_object('tbt_state2')
        self.imagemenuitem5 = self.builder.get_object('imagemenuitem5')
        self.imagemenuitem10 = self.builder.get_object('imagemenuitem10')
        self.builder.connect_signals(self)
        self.bufsize = 10  # ajout 20.02
        self.databuffer = collections.deque([0.0] * self.bufsize, self.bufsize)  # ajout 20.02
        self.x = [1 * i for i in range(-self.bufsize + 1, 1)]  # ajout 20.02(-self.bufsize+1,1)
        # Matplotlib trucs
        self.figure = Figure(figsize=(100, 100), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)  # une gtk.DrawingArea
        self.line, = self.ax.plot(self.x, self.databuffer)
        # Gtk trucs
        self.canvas.show()
        self.graphview = self.builder.get_object("plot")
        self.graphview.pack_start(self.canvas, True, True, True)
        self.arrow = self.builder.get_object('arrow1')
        self.window.connect('delete-event', self.quit)
        self.tbt_state0.connect('toggled', self.on_button_toggled0)
        self.tbt_state1.connect('toggled', self.on_button_toggled1)
        self.tbt_state2.connect('toggled', self.on_button_toggled2)
        self.bt_exit.connect('clicked', self.quit)
        self.imagemenuitem5.connect('activate', self.quit)
        self.imagemenuitem10.connect('activate', self.show_aboutdialog)
        self.window.show()
        # ================= Recherche du port de l'arduino ====================
        self.sonde = arduino.search()
        if self.sonde == "impossible d'ouvrir un port série":
            info = (self.sonde + "!" + '\n' +
                    "quitter cette session, vérifier la connexion avec le PLC, puis relancer le programme")
            self.ajout_log_term("TB", info)
        else:
            self.ajout_log_term("PLC", self.sonde)
            self.init_arduino()  # initialise l'arduino
        # =====================================================================

    def updateplot(self):
        self.databuffer.append(UI.yn)
        self.line.set_ydata(self.databuffer)
        self.ax.relim()
        self.ax.autoscale_view(False, False, True)
        self.canvas.draw()

    def on_button_toggled0(self, button):
        if button.get_active():
            state = ['1', 'on']
            button.set_label(state[1].upper())
            self.send_command(state[0])
            self.updateplot()  # pour marquer un temps...
            UI.xn = UI.xn + 1
            UI.yn = 0.8
        else:
            state = ['0', 'off']
            button.set_label(state[1].upper())
            self.send_command(state[0])
            self.updateplot()  # pour marquer un temps...
            UI.xn = UI.xn + 1
            UI.yn = 0
        # print(UI.xn, UI.yn)
        self.updateplot()
        # self.updateplot()
        # print 'Button0 was turned: ', state[1]

    def on_button_toggled1(self, button):
        if button.get_active():
            state = ['1', 'on']
            button.set_label(state[1].upper())
            self.send_command(state[0])
        else:
            state = ['0', 'off']
            button.set_label(state[1].upper())
            self.send_command(state[0])

    def on_button_toggled2(self, button):
        if button.get_active():
            state = ['1', 'on']
            button.set_label(state[1].upper())
            self.send_command(state[0])
        else:
            state = ['0', 'off']
            button.set_label(state[1].upper())
            self.send_command(state[0])

    def show_aboutdialog(self, *args):
        self.aboutdialog.run()
        self.aboutdialog.hide()

    def show_assistant(self, *args):
        self.assistant.show()
        self.assistant.hide()

    def quit(self, *args):
        if self.sonde != "impossible d'ouvrir un port série":
            self.quit_arduino()  # réinitialise l'arduino
        # Gtk.main_quit()    # voir commentaires lignes 21-25
        Gtk.main_quit()

    def init_arduino(self):
        arduino.open()
        time.sleep(4)
        arduino.write('0')  # éteint la led si elle était allumée
        arduino.flush()

    def quit_arduino(self):
        arduino.write('0')  # éteint la led si elle était allumée
        arduino.flush()
        arduino.close()

    def send_command(self, val):
        arduino.write(val)
        self.rec = arduino.reading()
        info = ("Bascule l'état de la led PLC à " + val)
        self.ajout_log_term("TB", info)
        info = self.rec.decode('utf-8').rstrip('\n\r')
        self.ajout_log_term("PLC", info)

    def ajout_log_term(self, src, msg):
        #self.textbuffer.insert_at_cursor(src + ": " + msg + '\n')
        # text_buffer is a gtk.TextBuffer
        start_iter = self.textbuffer.get_start_iter()
        self.textbuffer.insert(start_iter, (src + ": " + msg + '\n'))


# =====================================================================
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    arduino = Arduino()
    ui = UI()
    Gtk.main()  # voir commentaires lignes 21-25
    # gtk.main()
# =====================================================================
