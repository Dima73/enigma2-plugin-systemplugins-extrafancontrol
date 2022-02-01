#
# HddTempWatcher module for Enigma2 (HddTempWatcher.py)
# Based on hddtemp utils, so require install on system it
# Coded by vlamo (c) 2011
#
# Version: 0.6 (10.02.2017 22:00)
#

from Components.Harddisk import harddiskmanager
from enigma import eTimer
import os
import socket

plugin_hddtemp_db = "/usr/lib/enigma2/python/Plugins/SystemPlugins/ExtraFanControl/hddtemp.db"


class HddTempWatcher:
	BUFSIZE = 1024
	EUNKNOWN = -255
	EERROR = -254
	ESLEEP = -253
	ENAVAIL = -252

	def __init__(self, host="127.0.0.1", port=7634, devices="all", updatetime=60):
		self.hddlist = {}
		self.timer = eTimer()
		self.timer.callback.append(self.__updateHddTempData)
		if self.reloadHddTemp(host, port, devices, updatetime, False):
			if self.__updatetime:
				self.timer.start(0, True)

	def __updateHddTempData(self):
		if self.checkHddTemp():
			self.hddlist = self.getHddTempData()
		if self.__updatetime:
			self.timer.start(self.__updatetime * 1000, True)

	def checkHddTemp(self):
		ret = os.system("pidof hddtemp")
		if ret:
			return self.loadHddTemp()
		return True

	def reloadHddTemp(self, host="127.0.0.1", port=7634, devices="all", updatetime=60, update=True):
		self.__host = host
		self.__port = port
		self.__devices = devices
		self.__updatetime = updatetime

		os.system("killall -9 hddtemp")
		ret = self.loadHddTemp()

		if update:
			self.__updateHddTempData()
		return ret

	def loadHddTemp(self):
		if not os.path.exists("/usr/sbin/hddtemp"):
			return None
		hddlist = ""
		auto = self.__devices in ("", "all", "auto")
		devices = not auto and self.__devices.split() or []
		for hdd in harddiskmanager.HDDList():
			if self.isInternalDevice(hdd[1].phys_path):
				devdir = hdd[1].getDeviceDir()
				if auto:
					hddlist += " " + devdir
				else:
					for dev in devices:
						if dev == devdir:
							hddlist += " " + devdir
		if os.path.exists(plugin_hddtemp_db):
			if not os.path.exists("/usr/share/misc/hddtemp.db"):
				os.system("cp " + plugin_hddtemp_db + " /usr/share/misc/hddtemp.db")
			else:
				plugin_hddtemp_size = 0
				try:
					plugin_hddtemp_size = os.path.getsize(plugin_hddtemp_db)
				except:
					pass
				user_hddtemp_size = 0
				try:
					user_hddtemp_size = os.path.getsize("/usr/share/misc/hddtemp.db")
				except:
					pass
				if plugin_hddtemp_size and user_hddtemp_size and plugin_hddtemp_size > user_hddtemp_size:
					os.system("cp " + plugin_hddtemp_db + " /usr/share/misc/hddtemp.db")
		if not os.path.exists("/usr/share/misc/hddtemp.db"):
			return None
		if hddlist:
			cmd = 'hddtemp -d -l %s -p %d -s "|" -u "C" %s' % (self.__host, self.__port, hddlist)
			ret = os.system(cmd)
			if ret == 0:
				return True
		return None

	def isInternalDevice(self, phys_path):
		return "pci" in phys_path or "ahci" in phys_path or "sata" in phys_path

	def isRemovableDevice(self, device):
		removable = False
		try:
			fd = open('/sys/block/%s/removable' % (device), 'r')
			data = fd.read().strip()
			fd.close()
			removable = bool(int(data))
		except:
			print("[HddTempWatcher]: read removable state for device '%s' is failed" % (device))
		return removable

	def getHddTempData(self):
		data = ""
		hddlist = {}
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			s.connect((self.__host, self.__port))
			while True:
				buf = s.recv(self.BUFSIZE)
				if not len(buf):
					break
				data += buf
		except socket.error as e:
			print("[HddTempWatcher]: %s - %s:%d" % (e, self.__host, self.__port))
		s.close()

		if len(data):
			if data[0] == "|":
				data = data[1:]
			for i in data.split("||"):
				hdd = i.split("|")
				if len(hdd) > 3:
					sleep = False
					if not hdd[2].isdigit():
						if hdd[2] == "ERR":
							temp = self.EERROR
						elif hdd[2] == "SLP":
							temp = self.ESLEEP
							sleep = True
						elif hdd[2] == "NA":
							temp = self.ENAVAIL
						else:
							temp = self.EUNKNOWN
					else:
						temp = int(hdd[2])
					hddlist[hdd[0]] = {
						"path": hdd[0],
						"name": hdd[1],
						"temp": temp,
						"unit": hdd[3],
						"sleep": sleep,
					}
		return hddlist

	def getHddTempList(self):
		if not self.__updatetime:
			self.__updateHddTempData()
		return self.hddlist

#hddtempwatcher = HddTempWatcher()
