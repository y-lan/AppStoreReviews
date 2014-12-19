#!/usr/bin/env python
''' Apple AppStore reviews scrapper
    version 2011-04-12
    Tomek "Grych" Gryszkiewicz, grych@tg.pl
    http://www.tg.pl
    
    based on "Scraping AppStore Reviews" blog by Erica Sadun
     - http://blogs.oreilly.com/iphone/2008/08/scraping-appstore-reviews.html
    AppStore codes are based on "appstore_reviews" by Jeremy Wohl
     - https://github.com/jeremywohl/iphone-scripts/blob/master/appstore_reviews
'''
import urllib2
import sys
import string
import re
from urlparse import urlparse, parse_qs
import json
import time

from bs4 import BeautifulSoup, Tag
from elementtree import ElementTree
import argparse


appStores = {
    'Argentina': 143505,
    'Australia': 143460,
    'Belgium': 143446,
    'Brazil': 143503,
    'Canada': 143455,
    'Chile': 143483,
    'China': 143465,
    'Colombia': 143501,
    'Costa Rica': 143495,
    'Croatia': 143494,
    'Czech Republic': 143489,
    'Denmark': 143458,
    'Deutschland': 143443,
    'El Salvador': 143506,
    'Espana': 143454,
    'Finland': 143447,
    'France': 143442,
    'Greece': 143448,
    'Guatemala': 143504,
    'Hong Kong': 143463,
    'Hungary': 143482,
    'India': 143467,
    'Indonesia': 143476,
    'Ireland': 143449,
    'Israel': 143491,
    'Italia': 143450,
    'Korea': 143466,
    'Kuwait': 143493,
    'Lebanon': 143497,
    'Luxembourg': 143451,
    'Malaysia': 143473,
    'Mexico': 143468,
    'Nederland': 143452,
    'New Zealand': 143461,
    'Norway': 143457,
    'Osterreich': 143445,
    'Pakistan': 143477,
    'Panama': 143485,
    'Peru': 143507,
    'Phillipines': 143474,
    'Poland': 143478,
    'Portugal': 143453,
    'Qatar': 143498,
    'Romania': 143487,
    'Russia': 143469,
    'Saudi Arabia': 143479,
    'Schweiz/Suisse': 143459,
    'Singapore': 143464,
    'Slovakia': 143496,
    'Slovenia': 143499,
    'South Africa': 143472,
    'Sri Lanka': 143486,
    'Sweden': 143456,
    'Taiwan': 143470,
    'Thailand': 143475,
    'Turkey': 143480,
    'United Arab Emirates': 143481,
    'United Kingdom': 143444,
    'United States': 143441,
    'Venezuela': 143502,
    'Vietnam': 143471,
    'Japan': 143462,
    'Dominican Republic': 143508,
    'Ecuador': 143509,
    'Egypt': 143516,
    'Estonia': 143518,
    'Honduras': 143510,
    'Jamaica': 143511,
    'Kazakhstan': 143517,
    'Latvia': 143519,
    'Lithuania': 143520,
    'Macau': 143515,
    'Malta': 143521,
    'Moldova': 143523,
    'Nicaragua': 143512,
    'Paraguay': 143513,
    'Uruguay': 143514
}
userAgent = 'iTunes/9.2 (Macintosh; U; Mac OS X 10.6)'


def getReviews(appStoreId, appId, maxReviews=-1):
    ''' returns list of reviews for given AppStore ID and application Id
        return list format: [{"topic": unicode string, "review": unicode string, "rank": int}]
    '''
    reviews = []
    i = 0
    while True:
        print "crawling page %d (already %d reviews in box)" % (i, len(reviews))
        ret = _getReviewsForPage(appStoreId, appId, i)
        if len(ret) == 0:  # funny do while emulation ;)
            break
        reviews += ret
        i += 1
        if maxReviews > 0 and len(reviews) > maxReviews:
            break
    return reviews


def getReviewsByUser(appStoreId, userId, maxReviews=-1):
    reviews = []
    i = 0
    while True:
        ret = _getUserReviewsForPage(appStoreId, userId, i)
        if len(ret) == 0:
            break
        reviews += ret
        i += 1
        if maxReviews > 0 and len(reviews) > maxReviews:
            break
    return reviews


def format_date(str):
    str = str.strip()
    if str.startswith('Updated'):
        return 'Updated ' + format_date(str[7:])
    elif str.startswith('Released'):
        return 'Released ' + format_date(str[8:])
    else:
        fmt = "%Y-%m-%d"
        if re.match('^\w{3} \d{2}, \d{4}$', str):
            return time.strftime(fmt, time.strptime(str, "%b %d, %Y"))
        elif re.match('\d{2} \w+ \d{4}', str):
            return time.strftime(fmt, time.strptime(str, "%d %B %Y"))
        elif re.match('\d{4}', str):
            return time.strftime(fmt, time.strptime(str, "%Y"))
        else:
            raise ValueError(str)


def _getReviewsForPage(appStoreId, appId, pageNo):
    front = "%d-1" % appStoreId
    url = "https://itunes.apple.com/WebObjects/MZStore.woa/wa/viewContentsUserReviews?id=%s&pageNumber=%d&sortOrdering=4&onlyLatestVersion=false&type=Purple+Software" % (
        appId, pageNo)
    req = urllib2.Request(url, headers={"X-Apple-Store-Front": front, "User-Agent": userAgent})
    try:
        u = urllib2.urlopen(req, timeout=30)
    except urllib2.HTTPError:
        print "Can't connect to the AppStore, please try again later."
        raise SystemExit
    root = ElementTree.parse(u).getroot()

    app_node = root.find(
        '{http://www.apple.com/itms/}View/{http://www.apple.com/itms/}ScrollView/{http://www.apple.com/itms/}VBoxView'
        '/{http://www.apple.com/itms/}View/{http://www.apple.com/itms/}MatrixView/{http://www.apple.com/itms/}VBoxView'
        '/{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}VBoxView/{http://www.apple.com/itms/}VBoxView'
        '/{http://www.apple.com/itms/}MatrixView/{http://www.apple.com/itms/}VBoxView'
    )

    app_info_nodes = app_node.findall('{http://www.apple.com/itms/}TextView')

    name = app_info_nodes[0].find(
        "{http://www.apple.com/itms/}SetFontStyle/{http://www.apple.com/itms/}GotoURL").text.strip()
    genre = re.match('Category:(.*)$',
                     app_info_nodes[1].find("{http://www.apple.com/itms/}SetFontStyle").text.strip()).group(1).strip()
    publisher_id = ''
    publisher_name = (app_info_nodes[4].find("{http://www.apple.com/itms/}SetFontStyle").text.strip())[1:].strip()
    release_date = format_date(app_info_nodes[2].find("{http://www.apple.com/itms/}SetFontStyle").text)

    reviews = []
    for node in root.findall(
            '{http://www.apple.com/itms/}View/{http://www.apple.com/itms/}ScrollView/{http://www.apple.com/itms/}VBoxView'
            '/{http://www.apple.com/itms/}View/{http://www.apple.com/itms/}MatrixView/{http://www.apple.com/itms/}VBoxView'
            '/{http://www.apple.com/itms/}VBoxView/{http://www.apple.com/itms/}VBoxView/'
    ):
        review = {}
        review['app_id'] = appId
        review['app_genre'] = genre
        review['app_name'] = name
        review['app_publisher_id'] = publisher_id
        review['app_publisher_name'] = publisher_name
        review['app_release_date'] = release_date

        review_node = node.find("{http://www.apple.com/itms/}TextView/{http://www.apple.com/itms/}SetFontStyle")
        if review_node is None:
            review["review"] = None
        else:
            review["review"] = review_node.text

        version_node = node.find(
            "{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}TextView/{http://www.apple.com/itms/}SetFontStyle/{http://www.apple.com/itms/}GotoURL")
        if version_node is None:
            review["version"] = None
            review["user"] = None
            review["user_profile_id"] = None
        else:
            review["version"] = re.search("Version [^\n^\ ]+", version_node.tail).group()
            review["date"] = format_date(re.search("[^\n]+[\n\ ]*$", version_node.tail).group())
            review["user"] = version_node.text.strip()
            o = urlparse(version_node.attrib['url'])
            review["user_profile_id"] = long(parse_qs(o.query)['userProfileId'][0])

        # user_node = node.find("{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}TextView/{http://www.apple.com/itms/}SetFontStyle/{http://www.apple.com/itms/}GotoURL/{http://www.apple.com/itms/}b")

        rank_node = node.find(
            "{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}HBoxView")
        try:
            alt = rank_node.attrib['alt']
            st = int(alt.strip(' stars'))
            review["rank"] = st
        except KeyError:
            review["rank"] = None

        topic_node = node.find(
            "{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}TextView/{http://www.apple.com/itms/}SetFontStyle/{http://www.apple.com/itms/}b")
        if topic_node is None:
            review["topic"] = None
        else:
            review["topic"] = topic_node.text

        vote_node = node.find(
            "{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}HBoxView/{http://www.apple.com/itms/}VBoxView/{http://www.apple.com/itms/}GotoURL")
        if vote_node is None:
            review["id"] = None
        else:
            review["id"] = long(parse_qs(urlparse(vote_node.attrib['url']).query)['userReviewId'][0])

        reviews.append(review)
    return reviews


def _getUserReviewsForPage(appStoreId, userId, pageNo):
    front = "%d-2" % appStoreId
    url = "https://itunes.apple.com/WebObjects/MZStore.woa/wa/allUserReviewsForReviewerFragment?userProfileId=%s&page=%d&sort=14" % (
        userId, pageNo)
    req = urllib2.Request(url, headers={"X-Apple-Store-Front": front + ',12', "User-Agent": userAgent})
    try:
        u = urllib2.urlopen(req, timeout=30)
    except urllib2.HTTPError:
        print "Can't connect to the AppStore, please try again later."
        raise SystemExit
    soup = BeautifulSoup(u.read().decode('utf-8', 'ignore'))
    user = re.match('All Reviews by(.*)$', soup.find('div', {'class': 'main-title'}).get_text()).group(1).strip()
    reviews = []

    for node in soup.find_all('div', {'class': 'customer-review'}):
        review = {}
        review['id'] = long(parse_qs(urlparse(
            node.find('div', {'class': 'manage-block'}).find('span', {'class': 'report-a-concern'}).attrs[
                'report-a-concern-fragment-url']).query)['userReviewId'][0])

        comment = node.find('div', {'class': 'review-block'})

        review['topic'] = comment.find('div', {'class': 'title-text'}).get_text()
        rbuf = []
        for elem in comment.find('p').contents:
            if type(elem) is Tag and elem.name == 'br':
                rbuf.append("\n")
            else:
                rbuf.append(elem.extract())
        review['review'] = ('\n'.join(rbuf)).strip()
        review['date'] = format_date(comment.find('div', {'class': 'review-date'}).get_text())
        review['version'] = None
        review['rank'] = int(re.search("^\d*", comment.find('div', {'class': 'rating'}).attrs['aria-label']).group())

        review['user_profile_id'] = userId
        review['user'] = user

        app = node.find('div', {'class': 'lockup'})
        try:
            review['app_id'] = long(app.attrs['adam-id'])
            review['app_name'] = app.attrs['aria-label']
            review['app_publisher_id'] = urlparse(app.find('li', {'class': 'artist'}).find('a').attrs['href']).path
            review['app_publisher_name'] = app.find('li', {'class': 'artist'}).get_text()
            review['app_genre'] = app.find('li', {'class': 'genre'}).get_text()
            review['app_release_date'] = format_date(app.find('li', {'class': 'release-date'}).get_text())
        except AttributeError:
            review['app_id'] = None
            review['app_name'] = None
            review['app_publisher_id'] = None
            review['app_publisher_name'] = None
            review['app_genre'] = None
            review['app_release_date'] = None
        except ValueError:
            raise ValueError(userId)

        reviews.append(review)

    return reviews


def _print_reviews(reviews, country):
    ''' returns (reviews count, sum rank)
    '''
    if len(reviews) > 0:
        print "Reviews in %s:" % (country)
        print ""
        sumRank = 0
        for review in reviews:
            print "Review (%d) on Game %s (%s) by %s (%s) on %s" % (
                review["id"], review["app_name"], review["version"], review["user"], review["user_profile_id"],
                review["date"])
            for i in range(review["rank"]):
                sys.stdout.write(u"\u2605")  # to avoid space or newline after print
            print " %s\n%s" % (review["topic"], review["review"])
            print ""
            sumRank += review["rank"]
        print "Number of reviews in %s: %d, avg rank: %.2f\n" % (country, len(reviews), 1.0 * sumRank / len(reviews))
        return (len(reviews), sumRank)
    else:
        return (0, 0)


def _print_jsonmode(reviews):
    for review in reviews:
        print json.dumps(review)


def _print_rawmode(reviews):
    for review in reviews:
        print review["topic"], review["review"].replace("\n", "")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AppStoreReviewsScrapper command line.',
                                     epilog='To get your application Id look into the AppStore link to you app, for example http://itunes.apple.com/pl/app/autobuser-warszawa/id335042980?mt=8 - app Id is the number between "id" and "?mt=0"')
    parser.add_argument('-i', '--id', default=0, metavar='AppId', type=int, help='By Application Id')
    parser.add_argument('-u', '--uid', default=0, metavar='UserId', type=int, help='By User Id')
    parser.add_argument('-c', '--country', metavar='"Name"', type=str, default='all',
                        help='AppStore country name (use -l to see them)')
    parser.add_argument('-l', '--list', action='store_true', default=False, help='AppStores list')
    parser.add_argument('-m', '--max-reviews', default=-1, metavar='MaxReviews', type=int,
                        help='Max number of reviews to load')
    parser.add_argument('-r', '--raw-mode', action='store_true', default=False, help='Print in raw mode')
    parser.add_argument('-j', '--json-mode', action='store_true', default=False, help='Print in JSON mode')
    args = parser.parse_args()
    if args.id == 0 and args.uid == 0:
        parser.print_help()
        raise SystemExit

    country = string.capwords(args.country)
    countries = appStores.keys()
    countries.sort()

    if args.list:
        for c in countries:
            print c
    else:
        if country == "All":
            rankCount = 0;
            rankSum = 0
            for c in countries:
                reviews = getReviews(appStores[c], args.id, maxReviews=args.max_reviews)
                (rc, rs) = _print_reviews(reviews, c)
                rankCount += rc
                rankSum += rs
            print "\nTotal number of reviews: %d, avg rank: %.2f" % (rankCount, 1.0 * rankSum / rankCount)
        else:
            try:
                if args.uid != 0:
                    reviews = getReviewsByUser(appStores[country], args.uid, maxReviews=args.max_reviews)
                else:
                    reviews = getReviews(appStores[country], args.id, maxReviews=args.max_reviews)
            except KeyError:
                print "No such country %s!\n\nWell, it could exist in real life, but I dont know it." % country
            pass

            if args.raw_mode:
                _print_rawmode(reviews)
            elif args.json_mode:
                _print_jsonmode(reviews)
            else:
                _print_reviews(reviews, country)
