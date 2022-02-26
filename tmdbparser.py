from tmdbv3api import TMDb, TV, Search
import re
from torcategory import GuessCategoryUtils
from tortitle import parseMovieName
from difflib import SequenceMatcher


def transFromCCFCat(cat):
    if re.match('(movie|MV)', cat, re.I):
        return 'movie'
    elif re.match('TV', cat, re.I):
        return 'tv'
    else:
        return ''


def transToCCFCat(mediatype, originCat):
    if mediatype == 'tv':
        return 'TV'
    elif mediatype == 'movie':
        if not re.match('(movie|BDMVISO|MV)', originCat, re.I):
            return 'Movie'
    return originCat


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


class TMDbNameParser():
    def __init__(self, tmdb_api_key, tmdb_lang):
        self.ccfcat = ''
        self.title = ''
        self.year = ''
        self.tmdbid = 0
        self.season = ''
        self.episode = ''
        self.cntitle = ''
        self.resolution = ''
        self.group = ''

        if tmdb_api_key:
            self.tmdb = TMDb()
            self.tmdb.api_key = tmdb_api_key
            self.tmdb.language = tmdb_lang

    def parse(self, torname, TMDb=False):
        catutil = GuessCategoryUtils()
        self.ccfcat, self.group = catutil.guessByName(torname)
        self.resolution = catutil.resolution
        self.title, self.year, self.season, self.episode, self.cntitle = parseMovieName(
            torname)
        if self.season and (self.ccfcat != 'TV'):
            # print('Category fixed: ' + movieItem)
            self.ccfcat = 'TV'
        if self.ccfcat == 'TV':
            self.season = self.fixSeasonName(self.season)

        if TMDb:
            self.searchTMDb(self.title, transFromCCFCat(self.ccfcat),
                            self.year, self.cntitle)

    def fixSeasonName(self, seasonStr):
        if re.match(r'^Ep?\d+(-Ep?\d+)?$', seasonStr,
                    flags=re.I) or not seasonStr:
            return 'S01'
        else:
            return seasonStr.upper()

    def verifyYear(self, resultDate, cat):
        match = False
        resyear = self.year
        m = re.match('^(\d+)', resultDate)
        if m:
            resyear = m.group(0)
            intyear = int(resyear)
            if cat == 'tv':
                match = not (self.season == 'S01' and self.year and self.year not in [str(intyear-1), str(intyear), str(intyear+1)])
            else:
                match = not self.year or (self.year in [str(intyear-1), str(intyear), str(intyear+1)])
        if match:
            self.year = resyear
        return match

    def saveTmdbTVResult(self, result):
        match = False
        if hasattr(result, 'first_air_date'):
            match = self.verifyYear(result.first_air_date, 'tv')
        elif hasattr(result, 'release_date'):
            match = self.verifyYear(result.release_date, 'tv')

        if match:
            if hasattr(result, 'name'):
                self.title = result.name
                # print('name: ' + result.name)
            elif hasattr(result, 'original_name'):
                self.title = result.original_name
                # print('original_name: ' + result.original_name)
            if hasattr(result, 'media_type'):
                self.ccfcat = transToCCFCat(result.media_type, self.ccfcat)
            self.tmdbid = result.id
            print('Found [%d]: %s' % (self.tmdbid, self.title))
        else:
            print('\033[33mNot match in tmdb: [%s]\033[0m ' % (self.title))

        return match

    def saveTmdbMovieResult(self, result):
        match = False
        if hasattr(result, 'release_date'):
            match = self.verifyYear(result.release_date, 'movie')
        elif hasattr(result, 'first_air_date'):
            match = self.verifyYear(result.first_air_date, 'movie')

        if match:
            if hasattr(result, 'title'):
                self.title = result.title
                # print('title: ' + result.title)
            elif hasattr(result, 'original_title'):
                self.title = result.original_title
                # print('original_title: ' + result.original_title)
            if hasattr(result, 'media_type'):
                self.ccfcat = transToCCFCat(result.media_type, self.ccfcat)
            self.tmdbid = result.id
            print('Found [%d]: %s' % (self.tmdbid, self.title))
        else:
            print('\033[33mNot match in tmdb: [%s]\033[0m ' % (self.title))
        return match

    def imdbMultiQuery(self, title, year=None):
        search = Search()
        return search.multi({"query": title, "year": year, "page": 1})

    def sortByPopularity(resultList):
        newlist = sorted(resultList, key=lambda x: x.popularity, reverse=True)

    def searchTMDb(self, title, cat=None, year=None, cntitle=None):
        if cat == 'tv':
            searchList = [('tv',cntitle), ('tv', title), ('movie', cntitle), ('movie', title)]
        else:
            searchList = [('movie', cntitle), ('movie', title), ('tv',cntitle), ('tv', title)]

        for s in searchList:
            if s[0] == 'tv' and s[1]:
                tv = TV()
                print('Search TV: ' + s[1])
                results = tv.search(s[1])
                if len(results) > 0:
                    match = self.saveTmdbTVResult(results[0])
                    if match:
                        return self.tmdbid, self.title, self.year

            elif s[0] == 'movie' and s[1]:
                print('Search Movie: ' + s[1])
                search = Search()
                results = search.movies({"query": s[1], "year": year, "page": 1})
                if len(results) > 0:
                    match = self.saveTmdbMovieResult(results[0])
                    if match:
                        return self.tmdbid, self.title, self.year

        print('\033[31mTMDb Not found: [%s] [%s]\033[0m ' % (title, cntitle))
        return 0, title, year


if __name__ == '__main__':
    # itemName = '[我要打篮球].Game.On.2019.Complete.WEB-DL.1080p.H264.AAC-CMCTV'
    # itemName = 'Journey to the West (2011)'
    itemName = '人妖阿发 痴人三部曲⅓ Night of a Shemale A Mad Man Trilogy (2020)'
    print(itemName)
    # export TMDB_API_KEY='YOUR_API_KEY'
    p = TMDbNameParser('', 'zh-CN')
    p.parse(itemName, TMDb=True)
    print(p.title, p.year, p.ccfcat, p.tmdbid)