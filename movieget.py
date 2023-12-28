import requests
from bs4 import BeautifulSoup
import argparse
from datetime import datetime, timedelta
import logging
import csv
import re
import json

ALLO_CINE_ROOT = 'https://www.allocine.fr'


class Movie:

    def __init__(self, url):
        self.url = url
        self.sess = requests.session()
        self.movie_styles = []
        self.duration = 'unknown'
        self._parse()

    def _parse(self):

        html_text = self.sess.get(self.url).text
        self.movie_soup = BeautifulSoup(html_text, 'html.parser')
    
        # retrieve name
        self.name = self.movie_soup.find("meta", property="og:title")['content']
        
        # release date    
        # TODO: find better parsing logic
        to_parse = self.movie_soup.prettify()

        # get json containing movies info
        desc_script =self.movie_soup.find_all("script", {  "type" : "application/ld+json"}) #, itemtype=)

        if len(desc_script) == 1 :
            movie_inf = json.loads(desc_script[0].text)

            # process movie duration
            if 'duration' in movie_inf :
                self.duration = movie_inf['duration'][2:]

            # process movie style
            if 'genre' in movie_inf :
                style = movie_inf['genre']
                
                if isinstance(style, str) :
                    style = [ style ]
                self.movie_styles = style
        
        r = re.findall(r'"releaseDate":"([^"]+)"', to_parse, flags = re.MULTILINE)
        if r and len(r) >= 1 :
            self.release_date = datetime.strptime(r[0].split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
        else :
            self.release_date = 'FIXME'
        
        # hack: remove duplicate / in url
        self.url = self.url[:8] + self.url[8:].replace('//', '/')
                
    def __str__(self) :
        return '"{}", {}, {}, "{}", {}'.format(
            self.name, 
            self.release_date, 
            self.duration,
            ' ; '.join(self.movie_styles), 
            self.url)


    
    def get_movies_release_at(release_date):

        # craft ALLO_CINE URL
        movies_list_url = '{}/film/agenda/sem-{}'.format(ALLO_CINE_ROOT, release_date.strftime('%Y-%m-%d'))
        logging.debug('Getting movies released on {} using URL {}'.format(release_date, movies_list_url))

        # retrieve URL content
        sess = requests.session()
        url_content = sess.get(movies_list_url).text
        assert url_content
        soup = BeautifulSoup(url_content, 'html.parser')


        movie_list = []

        # TODO: ensure that link are in proper box to avoid getting invalid link
        for m in soup.find_all("a", "meta-title-link"):
            movie_url = '{}{}'.format(ALLO_CINE_ROOT, m['href'])
            movie = Movie(movie_url)
            print(movie)
            movie_list.append(movie)

        return movie_list

        
def _test():
    m = Movie('https://www.allocine.fr//film/fichefilm_gen_cfilm=1705.html')
    print(m)


def main():

    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s', 
        '--start', 
        type=lambda d: datetime.strptime(d, '%d/%m/%Y').date(), 
        help='start date (format dd-mm-yyyy)', 
        required=True)
    parser.add_argument('-c', '--count', help='week count (default 1)', type=int, default=1)
    parser.add_argument('-o', '--output', help="output csv file (default: movies.csv)", type=str, default="movies.csv")
    parser.add_argument('-v', '--verbose', help='verbose', action='store_true' )
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    

    release_date = args.start

    print("[!] getting movies list from {} weeks starting at {} (saving to {})".format(args.count, release_date, args.output))

    # retrieve movie list for every week requested
    f = open(args.output, 'w') 
    writer = csv.writer(f)
    writer.writerow(['semaine de sortie', 'nom', 'genre', 'date initiale sortie', 'url'])

    for _ in range(args.count) :
        movie_list =  Movie.get_movies_release_at(release_date) 

        for m in movie_list:
            writer.writerow([ release_date.strftime('%d/%m/%Y'), m.name, m.movie_styles, m.release_date, m.url])            
        # go to next week
        release_date += timedelta(days=7)

    
if __name__ == "__main__":
    main()

