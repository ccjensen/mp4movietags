#!/usr/bin/env python
#encoding:utf-8
#author:ccjensen/Chris
#project:mp4movietagger
#repository:http://github.com/ccjensen/mp4movietags
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)
 
"""
mp4movietags.py
Automatic Movie tagger.
Uses data from www.themoviedb.org

thanks goes to:
Rodney - http://kerstetter.net - for AtomicParsley help
dbr - http://github.com/dbr/themoviedb - for the API wrapper to TMDb
"""

__author__ = "ccjensen/Chris"
__version__ = "0.3"
 
import os
import sys
import re
from optparse import OptionParser
import tmdb

def openurl(urls):
    for url in urls:
        if len(url) > 0:
            os.popen("open \"%s\"" % url)
        #end if len
    #end for url
    return
#end openurl

def getDataFromTMDb(opts, movieName, movieYear):
    """docstring for getDataFromTMDb"""
    #download information from TMDb
    if opts.verbose:
        print "Retrieving data from TheMovieDB"
    #end if verbose
    movieResults = tmdb.search(movieName)
    movies = []
    
    #we got zero hits, try replacing some commonly used replacement-characters due to filename illegality
    if len(movieResults) < 1:
        if movieName.count(';'):
            tempMovieName = movieName.replace(';', ':')
            return getDataFromTheMovieDB(opts, tempMovieName, movieYear)
        elif movieName.count('_'):
            tempMovieName = movieName.replace('_', ' ')
            return getDataFromTheMovieDB(opts, tempMovieName, movieYear)
        else:
            return movies
        #end if count
    #end if len
    
    for movieResult in movieResults:
        movie = tmdb.getMovieInfo(movieResult['id'])
        #check that the year tag in the file name matches with the release date, otherwise not the movie we are looking for
        if movie['released'].startswith(str(movieYear)):
            movies.append(movie)
    #end for movie
    
    return movies
#end getDataFromTMDb


def tagFile(debug, verbose, forcetagging, movie, atomicParsley, additionalParameters):
    """docstring for tagFile"""
    if verbose:
        print "Tagging file..."
    #end if verbose
    
    #setup tags for the AtomicParsley function
    addArtwork = " --artwork \"%s\"" % movie['artworkFileName'] #the file we downloaded earlier
    addStik = " --stik value=\"0\"" #set type to Movie
    addTitle =  " --title \"%s\"" % movie['name']
    addDescription = " --description \"%s\"" % movie['overview']
    addLongDescription = " --longDescription \"%s\"" % movie['overview']
    addContentRating = " --contentRating \"%s\"" % "Unrated" #filler until TMDb support content rating
    addComment = " --comment \"tagged by mp4movietags\""
    
    if (movie['released'] == ""):
        addYear = ""
    else:
        addYear = " --year \"%sT07:00:00Z\"" % movie['released']
    
    genres = movie['categories']['genre'].keys()
    addGenre = " --genre \"%s\"" % genres[len(genres)-1]
    
    artist = ""
    for personID in movie['cast']['Director']:
        artist = movie['cast']['Director'][personID]['name']
        break #we only need one of the director's (if multiple)
    
    addArtist = " --artist \"%s\"" % artist
    
    #create rDNSatom
    castDNS = ""
    directorsDNS = ""
    producersDNS = ""
    screenwritersDNS = ""
    if len(movie['cast']['Actor']) > 0:
        actors = createNameArrayFromJobSpecificCastDict(movie['cast']['Actor'])
        castDNS = createrdnsatom("cast", actors)
    #end if len 
    if len(movie['cast']['Director']) > 0:
        directors = createNameArrayFromJobSpecificCastDict(movie['cast']['Director'])
        directorsDNS = createrdnsatom("directors", directors)
    #end if len
    if len(movie['cast']['Producer']) > 0:
        producers = createNameArrayFromJobSpecificCastDict(movie['cast']['Producer'])
        producersDNS = createrdnsatom("producers", producers)
    #end if len
    if len(movie['cast']['Author']) > 0:
        authors = createNameArrayFromJobSpecificCastDict(movie['cast']['Author'])
        screenwritersDNS = createrdnsatom("screenwriters", authors)
    #end if len
    
    #create the rDNSatom string
    addrDNSatom = " --rDNSatom \"<?xml version=\'1.0\' encoding=\'UTF-8\'?><plist version=\'1.0\'><dict>%s%s%s%s</dict></plist>\" name=iTunMOVI domain=com.apple.iTunes" % (castDNS, directorsDNS, producersDNS, screenwritersDNS)
    
    #Create the command line string
    tagCmd = "\"" + atomicParsley + "\" \"" + movie['fileName'] + "\"" + additionalParameters \
    + addArtwork + addStik + addArtist + addTitle + addGenre + addDescription + addContentRating \
    + addYear + addComment + addrDNSatom + addLongDescription
    
    
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

def createNameArrayFromJobSpecificCastDict(dict):
    """docstring for createNameArrayFromJobSpecificCastDict"""
    result = []
    for personID in dict:
        result.append(dict[personID]['name'])
    return result
#end createNameArrayFromJobSpecificCastDict

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
    parser = OptionParser(usage="%prog [options] <path to moviefile>\n%prog -h for full list of options")
    
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
                        help="Tags previously tagged files")
    parser.add_option(  "-r", "--remove-artwork", action="store_true", dest="removeartwork",
                        help="removes previously embeded artwork")
    parser.add_option(  "-t", "--no-tagging", action="store_false", dest="tagging",
                        help="disables tagging")
    parser.set_defaults( interactive=True, overwrite=True, debug=False, verbose=True, forcetagging=False,
                            removeartwork=False, tagging=True )
    
    opts, args = parser.parse_args()
    
    atomicParsley = os.path.join(sys.path[0], "AtomicParsley32")
    if not os.path.isfile(atomicParsley):
        sys.stderr.write("AtomicParsley is missing!\n")
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
        sys.stderr.write(args[0] + " is not a valid file\n")
        return 1
    #end if not os.path.isfile
    if opts.forcetagging:
        processingString = "Processing: %s [forced]" % args[0]
    else:
        processingString = "Processing: %s" % args[0]
    print processingString
    fileName = os.path.basename(args[0])
    (movieFileName, extension) = os.path.splitext(fileName)
    if not extension.count("mp4") and not extension.count("m4v"):
        sys.stderr.write("%s is of incorrect file type. Convert to h264 with extension mp4 or m4v\n" % fileName)
        return 2
    #end if not extension
    
    yearWithBrackets = re.compile("\([0-9]{4}\)")
    yearWithoutBrackets = re.compile("[0-9]{4}")
    try:
        movieYear = yearWithBrackets.findall(movieFileName)[0]
        movieName = movieFileName.replace(movieYear, '', 1).strip()
        movieYear = yearWithoutBrackets.findall(movieYear)[0]
    except:
        sys.stderr.write("%s is of incorrect syntax. Example: \"Movie Name (YEAR).m4v\"" % fileName)
        return 3
    #end try
    
    if opts.removeartwork:
        if opts.verbose:
            print "Removing any pre-existing embeded artwork from %s" % fileName
        #end if opts.verbose
        #remove any pre-existing embeded artwork
        os.popen("\"" + atomicParsley + "\" \"" + fileName + "\" --artwork REMOVE_ALL" + additionalParameters)
    #end if opts.removeartwork
    
    #============ embed information in file using AtomicParsley ============
    if opts.tagging:
        #check if user wishes to bypass already tagged check
        if not opts.forcetagging:
            #check if file has already been tagged
            if alreadyTagged(opts, atomicParsley, fileName):
                return 0
            #end if alreadyTagged
        #end if not forcetagging
        
        #============ TAG DATA ============ 
        movies = getDataFromTMDb(opts, movieName, movieYear)
        
        if len(movies) == 0:
            sys.stderr.write("No matches found for \"" + movieName + "\" made in " + movieYear + "\n")
            return 4
        
        if opts.interactive:
            print "\nPotential Title Matches"
            movieCounter = 0
            for movie in movies:
                print "%s. %s (ID: %s)" % (movieCounter, movie['name'], movie['id'])
                movieCounter = movieCounter + 1
            #end for movie in movies
    
            #ask user what movie he wants to use
            movieChoice = int(raw_input("Select correct title: "))
        else:
            movieChoice = 0
        #end if interactive
        
        movie = movies[movieChoice]
        
        #============ ARTWORK ============ 
        artworksPreview = []
        artworksLarge = []
        for ids in movie['images']['poster']:
            artworksPreview.append(movie['images']['poster'][ids]['mid'])
            artworksLarge.append(movie['images']['poster'][ids]['original'])
        #end for ids
        
        if opts.interactive:
            artworkCounter = 0
            print "\nList of available artwork"
            for artwork in artworksPreview:
                print "%s. %s" % (artworkCounter, artwork)
                artworkCounter += 1
            #end for artwork
    
            #allow user to preview images
            print "Example of listing: 0 2 4"
            artworkPreviewRequestNumbers = raw_input("List Images to Preview: ")
            artworkPreviewRequests = artworkPreviewRequestNumbers.split()
    
            artworkPreviewUrls = []
            for artworkPreviewRequest in artworkPreviewRequests:
                artworkPreviewUrls.append(artworksPreview[int(artworkPreviewRequest)])
            #end for artworkPreviewRequest
            openurl(artworkPreviewUrls)
    
            #ask user what artwork he wants to use
            artworkChoice = int(raw_input("Artwork to use: "))
        else:
            artworkChoice = 0
        #end if interactive
        
        artworkUrl = artworksLarge[artworkChoice]
        
        #download artwork to use
        (artworkUrl_base, artworkUrl_fileName) = os.path.split(artworkUrl)
        (artworkUrl_baseFileName, artworkUrl_fileNameExtension)=os.path.splitext(artworkUrl_fileName)
    
        artworkFileName = movieFileName + artworkUrl_fileNameExtension
        if opts.verbose:
            print "Downloaded Artwork: " + artworkFileName
        #end if verbose
        os.popen("curl -o \"%s\" \"%s\"" % (artworkFileName, artworkUrl))
        
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
