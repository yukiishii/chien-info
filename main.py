#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import wsgiref.handlers
import urllib
import os
import re
import datetime

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import xmpp
import xml.etree.ElementTree as etree

class dataStore(db.Model):
    keyword = db.StringProperty()
    #content = db.BlobProperty()
    content = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return datetime.timedelta(0)

class JST(datetime.tzinfo):
    def utcoffset(self,dt):
        return datetime.timedelta(hours=9)
    def dst(self,dt):
        return datetime.timedelta(0)
    def tzname(self,dt):
        return "JST"

class twitter():
  def get( self, keyword ):
    url = 'http://search.twitter.com/search.atom?'
    result = urlfetch.fetch( url+'q='+keyword+'&lang=ja' )
    return result

  def search( self, keyword ):
    keyword = keyword.encode('utf-8');

    url = 'http://search.twitter.com/search.atom?'
    #query = [
    #  ('q', keyword),
    #  ]
    #form_data = urllib.urlencode(query)
    #result = urlfetch.fetch( url+form_data+'&lang=ja' )
    #self.response.out.write( url+ form_data )
    #result = urlfetch.fetch( url+'q='+keyword+'&lang=ja' )
    result = self.get( keyword )
    
    i=0
    while result.status_code != 200:
      result = self.get( keyword )
      i+=1;
      if 2<i:
        #key = str(keyword).replace("%","")
        #result.content = db.get( db.Key(str("key" + key[0:10])).name() )
        #result.content = dataStore.get_by_key_name("key" + key[0:10] ).content
        result.content = dataStore.get_by_key_name( keyword ).content
        #q = dataStore.all()
        #result.content = q.filter("keyword =", keyword).fetch(limit=3, offset=0).pop().content
        break

    if i!=3:
      #key = str(keyword).replace("%","")
      #ds = dataStore( key_name="key"+key[0:10], keyword=keyword, content=result.content )
      ds = dataStore( key_name=keyword, keyword=keyword, content=result.content )
      ds.put()
    
    xml = etree.fromstring( result.content )
#    if result.status_code == 200:
#      xml = etree.fromstring( result.content )
#    else:
#      result = urlfetch.fetch( url+'q='+keyword+'&lang=ja' )
#      xml = etree.fromstring( result.content )
      
    params  = []
    for entries in xml.getiterator("{http://www.w3.org/2005/Atom}entry"):
      #self.response.out.write( entries.tag )
      name = entries.find(".//{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name").text
      p = re.compile( '\(.*\)' )
      name = p.sub( '', name )
      
      time = entries.find("{http://www.w3.org/2005/Atom}published").text
      
      dt = datetime.datetime.strptime( time, "%Y-%m-%dT%H:%M:%SZ")
      time = dt.replace(tzinfo=UTC()).astimezone(JST())
      time = str(time).replace( "+09:00", "" )
      
      param = { "img" : entries.findall("{http://www.w3.org/2005/Atom}link")[1].get("href"),
                "name" : name,
                "content" : entries.find("{http://www.w3.org/2005/Atom}content").text,
                "uri": entries.find(".//{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}uri").text,
                "time" : time,
                }
      
      params.append( param )
    

    
    return params


class MainHandler(webapp.RequestHandler):

  def get(self):
    #self.response.out.write('Hello world!')
    params = memcache.get("index")
    if params is not None:
      template_values = {
        'params': params,
        }
    else:
      #keyword = urllib.urlencode(u"遅延".encode('utf-8'));
      keyword = urllib.quote(u"線 遅延 OR 線 遅れ".encode('utf-8'))
      tw = twitter()
      params = tw.search(keyword)
      template_values = {
        'params': params,
        }
      if not memcache.add("index", params, 120):
        logging.error("Memcache set failed.")
    
    p = re.compile( '.*iPhone.*' )
    if p.search( self.request.user_agent ):
        path = os.path.join(os.path.dirname(__file__), 'tmpl/index_iphone.html')
    else:
        path = os.path.join(os.path.dirname(__file__), 'tmpl/index.html')
    self.response.out.write(template.render(path, template_values))

class iphone(webapp.RequestHandler):

  def get(self):
      path = os.path.join(os.path.dirname(__file__), 'tmpl/iphone.html')
      self.response.out.write(template.render(path, ''))

class mixi_manu(webapp.RequestHandler):

  def get(self):
      path = os.path.join(os.path.dirname(__file__), 'tmpl/mixi_manu.html')
      self.response.out.write(template.render(path, ''))

class page(webapp.RequestHandler):

  def get(self, arg):
    #self.response.out.write( page )
    params = memcache.get(arg)
    if params is not None:
      template_values = {
        'params': params,
        'name'  : urllib.unquote_plus(arg.encode('utf8')),
        }
    else:
      tw = twitter()
      params = tw.search(arg)
      template_values = {
        'params': params,
        'name'  : urllib.unquote_plus(arg.encode('utf8')),
        }
      if not memcache.add(arg, params, 120):
        logging.error("Memcache set failed.")

    path = os.path.join(os.path.dirname(__file__), 'tmpl/twitter_search.html')
    self.response.out.write(template.render(path, template_values))
      
class about(webapp.RequestHandler):

  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'tmpl/about.html')
    self.response.out.write(template.render(path, ''))

class mixi(webapp.RequestHandler):

  def get(self):
    #params = memcache.get("mixi")
    #if params is not None:
    #  template_values = {
    #    'params': params,
    #    }
    #else:
      #keyword = urllib.urlencode(u"遅延".encode('utf-8'));
    keyword = urllib.quote(u"線 遅延 OR 線 遅れ".encode('utf-8'))
    tw = twitter()
    params = tw.search(keyword)
    template_values = {
      'params': params,
      }
      #if not memcache.add("mixi", params, 120):
      #  logging.error("Memcache set failed.")
    
    path = os.path.join(os.path.dirname(__file__), 'tmpl/mixi.html')
    self.response.out.write(template.render(path, template_values))

class debug(webapp.RequestHandler):
    
  def get(self):
      keyword = urllib.quote(u"線 遅延 OR 線 遅れ".encode('utf-8'))
      result = dataStore.get_by_key_name( keyword ).content

      print result
      p = re.compile( '.*Safari.*' )
      if p.search( self.request.user_agent ):
          print self.request.user_agent
      else:
          print result

class push(webapp.RequestHandler):
    
  def get(self):
      addr = "yuki.ishii@gmail.com"
  
      if xmpp.get_presence(addr):
          xmpp.send_message(addr, "Hello, Yuki!!")
      print self.request.user_agent

def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                        (r'/page/(.*)', page),
                                        ('/about', about),
                                        ('/iphone', iphone),
                                        ('/mixi', mixi_manu),
                                        ('/app/mixi', mixi),
                                        ('/push', push),
                                        ('/debug', debug)],
                                       
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
