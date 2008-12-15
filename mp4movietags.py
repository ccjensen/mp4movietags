#!/usr/bin/env python
#encoding:utf-8
#author:ccjensen/Chris
#project:mp4movietagger
#repository:http://github.com/ccjensen/mp4movietags/
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)
 
"""
mp4movietags.py
Automatic Movie tagger.
Uses data from www.tagchimp.com

thanks goes to:
Rodney - http://kerstetter.net - for AtomicParsley help
"""

__author__ = "ccjensen/Chris"
__version__ = "0.2"
 
import os
import sys
import re
import urllib
from xml.dom import minidom
from optparse import OptionParser

def getDataFromTagChimp(opts, config, movieName, movieYear):
	"""docstring for getDataFromTagChimp"""
	if opts.kind:
		#ask user what movie he wants to use
		movieLimit = int(raw_input("Select number of titles to return: "))
		url = config['url_getMovies'] % (movieName.replace(' ', '+'), movieLimit)
	else:
		url = config['url_getMovies'] % (movieName.replace(' ', '+'))
	#end if opts.kind
	#download information from tagchimp
	if opts.verbose:
		print "Retrieving data from Tag Chimp"
	#end if verbose
	urllib.urlretrieve(url, os.getcwd() + "/temp.xml")
	
	o = open("temp2.xml","w") #open for overwrite
	for line in open("temp.xml"):
		line = line.decode('utf-8')
		line = re.sub(">[^a-zA-Z0-9_<]",">",line)
		o.write(line.encode('utf-8') + "\n")
	o.close()
	
	dom = minidom.parse(os.getcwd() + "/temp2.xml")
	
	hits = dom.getElementsByTagName('movie')
	
	movies = []
	
	#we got zero hits, try replacing some commonly used replacement-characters due to filename illegality
	if len(hits) < 1:
		if movieName.count(';'):
			tempMovieName = movieName.replace(';', ':')
			return getDataFromTagChimp(opts, config, tempMovieName, movieYear)
		elif movieName.count('_'):
			tempMovieName = movieName.replace('_', ' ')
			return getDataFromTagChimp(opts, config, tempMovieName, movieYear)
		else:
			return movies
		#end if count
	#end if len
	
	for node in hits:
		movie = {}
		movie['movieID'] = node.getElementsByTagName('movieID')[0].childNodes[0].nodeValue		
		
		#traverse deeper
		subnode = node.getElementsByTagName('info')[0]
		
		movie['releaseDate'] = getSingleNode(subnode, 'releaseDate')
		
		#check that the year tag in the file name matches with the release date, otherwise not the movie we are looking for
		if not movie['releaseDate'].startswith(str(movieYear)):
			continue
		
		movie['movieTitle'] = getSingleNode(subnode, 'movieTitle')
		movie['category'] = getSingleNode(subnode, 'category')
		movie['rating'] = getSingleNode(subnode, 'rating')
		movie['shortDescription'] = getSingleNode(subnode, 'shortDescription')
		movie['longDescription'] = getSingleNode(subnode, 'longDescription')
		movie['rating'] = getSingleNode(subnode, 'rating')		
		
		movie['directors'] = getMultiNode(subnode, 'director')
		
		movie['producers'] = getMultiNode(subnode, 'producer')
		movie['screenwriters'] = getMultiNode(subnode, 'screenwriter')
		movie['cast'] = getMultiNode(subnode, 'actor')
		
		#done with deep traversal
		#clean up artwork url
		artworkURL = node.getElementsByTagName('coverArtLarge')[0].childNodes[0].nodeValue
		artworkURL = artworkURL.replace('[', '%5B')
		artworkURL = artworkURL.replace(']', '%5D')
		movie['coverArtLarge'] = artworkURL
		
		movies.append(movie)
	#end for node
	
	#remove temporary files
	os.remove(os.getcwd() + "/temp.xml")
	os.remove(os.getcwd() + "/temp2.xml")
	
	return movies
#end getDataFromTagChimp

def getMultiNode(subnode, xmltag):
	"""docstring for getMultiNode"""
	values = []
	for value in subnode.getElementsByTagName(xmltag):
		if len(value.childNodes) > 0:
			zerothNode = value.childNodes[0]
			values.append(zerothNode.nodeValue)
	return values
#end getMultiNode

def getSingleNode(subnode, xmltag):
	"""docstring for getSingleNode"""
	elements = subnode.getElementsByTagName(xmltag)
	if elements:
		parentOfNodes = elements[0]
		nodeList = parentOfNodes.childNodes
		if(len(nodeList) == 0):
			return ""
		#end if
		zerothNode = nodeList[0]
		thisNodeValue = zerothNode.nodeValue
	else:
		return ""
	#thisNodeValue = thisNodeValue.replace("'","\\\'")
	thisNodeValue = thisNodeValue.replace('"','\\\"')
	return thisNodeValue
#end getSingleNode

def arrayToCSVString(array):
	"""docstring for arrayToCSVString"""
	values = ""
	for value in array:
		if len(values) < 1:
			values = values + value
		else:
			values = values + ", " + value
		#end if len(cast)
	#end for actor
	return values
#end arrayToCSVString

def tagFile(debug, verbose, forcetagging, movie, atomicParsley, additionalParameters):
	"""docstring for tagFile"""
	if verbose:
		print "Tagging file..."
	#end if verbose
	
	#setup tags for the AtomicParsley function
	addArtwork = " --artwork \"%s\"" % movie['artworkFileName'] #the file we downloaded earlier
	addStik = " --stik value=\"0\"" #set type to Movie
	addArtist = " --artist \"%s\"" % arrayToCSVString(movie['cast'])
	addTitle =  " --title \"%s\"" % movie['movieTitle']
	addGenre = " --genre \"%s\"" % movie['category'] #cause first one is an empty string, and genre can only have one entry
	addDescription = " --description \"%s\"" % movie['shortDescription']
	addLongDescription = " --longDescription \"%s\"" % movie['longDescription']
	addContentRating = " --contentRating \"%s\"" % movie['rating']
	addYear = " --year \"%s\"" % movie['releaseDate']
	addSortOrderName = " --sortOrder name \"%s\"" % movie['movieTitle']
	addSortOrderArtist = " --sortOrder artist \"%s\"" % arrayToCSVString(movie['cast'])
	addComment = " --comment \"tagged by mp4movietags\""
	
	#concatunate actors and guest stars
	#actors = series.actors + episode.guestStars #usually makes a ridicously long list
	#create rDNSatom
	castDNS = ""
	directorsDNS = ""
	producersDNS = ""
	screenwritersDNS = ""
	if len(movie['cast']) > 0:
		castDNS = createrdnsatom("cast", movie['cast'])
	#end if len	
	if len(movie['directors']) > 0:
		directorsDNS = createrdnsatom("directors", movie['directors'])
	#end if len
	if len(movie['producers']) > 0:
		producersDNS = createrdnsatom("producers", movie['producers'])
	#end if len
	if len(movie['screenwriters']) > 0:
		screenwritersDNS = createrdnsatom("screenwriters", movie['screenwriters'])
	#end if len
	
	#create the rDNSatom string
	addrDNSatom = " --rDNSatom \"<?xml version=\'1.0\' encoding=\'UTF-8\'?><plist version=\'1.0\'><dict>%s%s%s%s</dict></plist>\" name=iTunMOVI domain=com.apple.iTunes" % (castDNS, directorsDNS, producersDNS, screenwritersDNS)
	
	#Create the command line string
	tagCmd = "\"" + atomicParsley + "\" \"" + movie['fileName'] + "\"" + additionalParameters \
	+ addArtwork + addStik + addArtist + addTitle + addGenre + addDescription + addSortOrderName \
	+ addSortOrderArtist + addContentRating  + addYear + addComment + addrDNSatom + addLongDescription
	
	
	#run AtomicParsley using the arguments we have created
	if debug:
		print tagCmd
	#end if debug
	
	os.popen(tagCmd.encode("utf-8"))
	
	lockCmd = "chflags uchg \"" + movie['fileName'] + "\""
	
	os.popen(lockCmd.encode("utf-8"))
	if verbose:
		print "Tagged and locked: " + movie['fileName']
	#end if verbose
#end tagFile

def alreadyTagged(opts, atomicParsley, fileName):
	"""docstring for checkIfAlreadyTagged"""
	#check if file has already been tagged
	cmd = "\"" + atomicParsley + "\" \"" + os.getcwd() + "/" + fileName + "\"" + " -t"
	existingTagsUnsplit = os.popen(cmd).read()
	existingTags = existingTagsUnsplit.split('\r')
	for line in existingTags:
		if line.count("tagged by mp4movietags"):
			if opts.verbose:
				print fileName + " already tagged"
			#end if verbose
			return True
		#end if line.count
	#end for line
	return False
#end checkIfAlreadyTagged

def createrdnsatom(key, array):
	"""docstring for createrdnsatom"""
	dns = "<key>" + key + "</key><array>"
	for item in array:
		if len(array) > 0:
			if len(item) > 0:
				dns += "<dict><key>name</key><string>%s</string></dict>" % item
			#end if len
		#end if len
	#end for actor
	dns += "</array>"
	return dns
#end createrdnsatom

def main():	
	parser = OptionParser(usage="%prog [options] <full path directory>\n%prog -h for full list of options")
	
	parser.add_option(  "-b", "--batch", action="store_false", dest="interactive",
	                    help="selects first search result, requires no human intervention once launched")
	parser.add_option(  "-i", "--interactive", action="store_true", dest="interactive",
	                    help="interactivly select correct movie from search results [default]")
	parser.add_option(  "-c", "--cautious", action="store_false", dest="overwrite", 
	                    help="Writes everything to new files. Nothing is deleted (will make a mess!)")
	parser.add_option(  "-d", "--debug", action="store_true", dest="debug", 
	                    help="shows all debugging info")
	parser.add_option(  "-v", "--verbose", action="store_true", dest="verbose",
	                    help="Will provide some feedback [default]")
	parser.add_option(  "-q", "--quiet", action="store_false", dest="verbose",
	                    help="For ninja-like processing")
	parser.add_option(  "-f", "--force-tagging", action="store_true", dest="forcetagging",
	                    help="Tags all valid files, even previously tagged ones")
	parser.add_option(  "-r", "--remove-artwork", action="store_true", dest="removeartwork",
	                    help="removes previously embeded artwork")
	parser.add_option(  "-t", "--no-tagging", action="store_false", dest="tagging",
	                    help="disables tagging")
	parser.add_option(  "-k", "--kind", action="store_true", dest="kind",
	                    help="allows non-locked entries (less complete?)")
	parser.set_defaults( interactive=True, overwrite=True, debug=False, verbose=True, forcetagging=False,
	 						removeartwork=False, tagging=True, kind=False )
	
	opts, args = parser.parse_args()
	
	config = {}
	
	config['apikey'] = "83261882249061D87D1778" # tagchimp.com API key
	
	if opts.kind:
		config['url_getMovies'] = "https://www.tagchimp.com/ape/lookup.php?token=%(apikey)s&type=search&title=%%s&videoKind=Movie&totalChapters=1&limit=%%s" % config
	else:
		config['url_getMovies'] = "https://www.tagchimp.com/ape/lookup.php?token=%(apikey)s&type=search&title=%%s&videoKind=Movie&totalChapters=1&limit=4&locked=true" % config
	#end if opts.kind
	
	atomicParsley = os.path.join(sys.path[0], "AtomicParsley32")
	if not os.path.isfile(atomicParsley):
		sys.stderr.write("AtomicParsley is missing!")
		return -1
	#end if not os.path.isfile
	
	if opts.overwrite:
		additionalParameters = " --overWrite"
	else:
		additionalParameters = ""
	#end if opts.overwrite
	
	if len(args) == 0:
	    parser.error("No file supplied")
	#end if len(args)
	
	if len(args) > 1:
	    parser.error("Provide single file")
	#end if len(args)
	
	if not os.path.isfile(args[0]):
		sys.stderr.write(args[0] + " is not a valid file")
		return 1
	#end if not os.path.isfile
	print "Processing: %s" % args[0]
	fileName = os.path.basename(args[0])
	(movieFileName, extension) = os.path.splitext(fileName)
	if not extension.count("mp4") and not extension.count("m4v"):
		sys.stderr.write("%s is of incorrect file type. Convert to h264 with extension mp4 or m4v\"") % fileName
		return 2
	#end if not extension
	
	yearWithBrackets = re.compile("\([0-9]{4}\)")
	yearWithoutBrackets = re.compile("[0-9]{4}")
	try:
		movieYear = yearWithBrackets.findall(movieFileName)[0]
		movieName = movieFileName.replace(movieYear, '', 1).strip()
		movieYear = yearWithoutBrackets.findall(movieYear)[0]
	except:
		sys.stderr.write("%s is of incorrect syntax. Example: \"Movie Name (YEAR).m4v\"") % fileName
		return 3
	#end try
	
	if opts.removeartwork:
		if opts.verbose:
			print "Removing any pre-existing embeded artwork from %s" % fileName
		#end if opts.verbose
		#remove any pre-existing embeded artwork
		os.popen("\"" + atomicParsley + "\" \"" + fileName + "\" --artwork REMOVE_ALL" + additionalParameters)
	#end if opts.removeartwork
	
	#embed information in file using AtomicParsley
	if opts.tagging:
		#check if user wishes to bypass already tagged check
		if not opts.forcetagging:
			#check if file has already been tagged
			if alreadyTagged(opts, atomicParsley, fileName):
				return 0
			#end if alreadyTagged
		#end if not forcetagging
		
		#retrieves data from tag chimp
		movies = getDataFromTagChimp(opts, config, movieName, movieYear)
		
		if len(movies) == 0:
			sys.stderr.write("No matches found for \"" + movieName + "\" made in " + movieYear + "\n")
			return 4
		
		if opts.interactive:
			print "\nPotential Title Matches"
			movieCounter = 0
			for movie in movies:
				print "%s. %s (ID: %s)" % (movieCounter, movie['movieTitle'], movie['movieID'])
				movieCounter = movieCounter + 1
			#end for movie in movies
	
			#ask user what movie he wants to use
			movieChoice = int(raw_input("Select correct title: "))
		else:
			movieChoice = 0
		#end if interactive
	
		movie = movies[movieChoice]
		
		#download artwork to use
		(artworkUrl_base, artworkUrl_fileName) = os.path.split(movie['coverArtLarge'])
		(artworkUrl_baseFileName, artworkUrl_fileNameExtension)=os.path.splitext(artworkUrl_fileName)
	
		artworkFileName = movieFileName + artworkUrl_fileNameExtension
		
		if opts.verbose:
			os.popen("curl -o \"%s\" '%s'" % (artworkFileName, movie['coverArtLarge']))
			print "Downloaded Artwork: " + artworkFileName
		else:
			os.popen("curl -o \"%s\" \"%s\"" % (artworkFileName, movie['coverArtLarge']))
		#end if verbose
		
		#update movie dict with filenames
		movie['fileName'] = fileName
		movie['artworkFileName'] = artworkFileName
	
		tagFile(opts.debug, opts.verbose, opts.forcetagging, movie, atomicParsley, additionalParameters)
	
		os.remove(artworkFileName)
		if opts.verbose:
			print "Deleted temporary artwork file created by mp4movietags"
		#end if opts.verbose
	#end if opts.tagging
	
	return 0
	

if __name__ == "__main__":
	sys.exit(main())
