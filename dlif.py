import cherrypy
import os
import stat
import base64
import hashlib
from functools import cmp_to_key
from time import strftime, mktime
from datetime import datetime, timedelta
from time import time
from jinja2 import Environment, FileSystemLoader
from urllib.request import pathname2url,url2pathname
from urllib.parse import urlencode

env = Environment(loader=FileSystemLoader('templates'))

def get_path_offset(path, offset = None):
 return len(os.path.normpath(path)[:offset])

def gen_secret(path, secret, timestamp, offset = None):
  offset_len = get_path_offset(path, offset)

  secret = ''.join([secret, '/s' + path[:offset],
                    str(timestamp), str(offset_len)])
  h_md5 = hashlib.new('md5')
  h_md5.update(secret.encode('utf-8'))
  hash_pass = h_md5.digest()
  hash_64 = base64.urlsafe_b64encode(hash_pass)
  security  = hash_64.rstrip(b'=').decode('utf-8')

  return offset_len, security, timestamp

def humnbr(size, precision=2):
  abbrevs = ((1<<50, 'PB'),(1<<40, 'TB'),(1<<30, 'GB'),
             (1<<20, 'MB'),(1<<10, 'kB'),(1, 'bytes'))
  if size == 1:
      return '1 byte'
  for factor, suffix in abbrevs:
      if size >= factor:
          break
  return ('%.*f %s' % (precision, size / factor, suffix)).replace('.00', '')

def humdate(m_time):
  return datetime.fromtimestamp(m_time).strftime("%Y-%m-%d %H:%M:%S")

def ez_stat(path1, path2):
  st = os.stat(os.path.join(path1, path2))
  return path2, st, stat.S_ISDIR(st.st_mode)

def args_for(**kwargs):
  s = ''
  for k, v in kwargs.items():
    s += '&%s=%s' % (k, v)
  return s.lstrip('&')

class Root:
    @cherrypy.expose
    def index(self, s='d', p='/', share=False, *args, **kwargs):
        if share:
          tmpl = env.get_template('share.html')
        else:
          tmpl = env.get_template('index.html')
        lst = []
        dir_name = cherrypy.request.app.config['dlif']['dir_name']
        time_limit = int(cherrypy.request.app.config['dlif']['time_limit'])
        secret = cherrypy.request.app.config['dlif']['secret']
        
        p = os.path.normpath(p).lstrip('/')
        abs_path = os.path.normpath(os.path.join(dir_name, p))
        timestamp = kwargs['e'] if 'e' in kwargs else int(time()) + time_limit
        if len(abs_path) > len(dir_name):
          data = {'name': '..', 'size': '-',
                  'date': '-',
                  'url' : '/'+pathname2url(os.path.normpath(os.path.join(p, '..'))),
                  'dir' : True}

          if share:
            offset = kwargs['pt']
            secret = kwargs['st']
            ttl = kwargs['e']
          else:
            offset, secret, ttl = gen_secret('/'+pathname2url(data['url']),
                                                 secret, timestamp)
          data['share_arg'] = args_for(pt=offset,st=secret,e=ttl)
          data['share'] = share
          print(share)
          if not share or get_path_offset('/'+pathname2url(data['url'])) > int(offset):
            lst.append(data)
        else:
          abs_path = dir_name
        fl_dir = os.listdir(abs_path)
        p = abs_path[len(dir_name):]
        fl = [ez_stat(abs_path, i) for i in fl_dir]
        rev = not (s[1:] == 'r')
        if s[:1] == 'f':
          fl.sort(key=lambda s: s[0], reverse=rev)
        elif s[:1] == 's':
          fl.sort(key=lambda s: s[1].st_size, reverse=rev)
        else:
          fl.sort(key=lambda s: s[1].st_mtime, reverse=rev)
          s = 'd'
        for name, st, isdir in fl:
          data = {'name': name, 'size': humnbr(st.st_size),
                  'date': humdate(st.st_mtime),
                  'url': pathname2url(p + '/' + name),
                  'dir': isdir}
          if share and isdir:
            offset = kwargs['pt']
            secret = kwargs['st']
            ttl = kwargs['e']
          else:
            offset, secret, ttl = gen_secret(p + '/' + name,
                                            secret, timestamp)
          data['share_arg'] = args_for(pt=offset,st=secret,e=ttl)
          data['share'] = True
          lst.append(data)
        sets = {'sort': s, 'path': pathname2url(p) }
        if share:
            sets['secargs'] = args_for(pt=kwargs['pt'],
                                       st=kwargs['st'],
                                       e=kwargs['e'])
            t_left_secs = int(kwargs['e']) - int(time())
            sets['timeleft'] = str(timedelta(seconds=t_left_secs))
        return tmpl.render(flst=lst, settings=sets, rev=rev, sort=s[:1])

    @cherrypy.expose
    def i(self, *args, **kwargs):
        try:
          _p = url2pathname(kwargs['p'])
          _e = int(kwargs['e'])
          _pt = int(kwargs['pt'])
          _st = kwargs['st']
          secret = cherrypy.request.app.config['dlif']['secret']

          pt, st, ttl = gen_secret(_p, secret, _e, _pt)
          print((_p, pt, st, ttl))
          if pt < _pt or _st != st or ttl != _e or _e < int(time()):
            raise Exception()
        except:
          return ''
        kwargs['share'] = True
        return self.index(*args, **kwargs)

cherrypy.config.update({'server.socket_host': '0.0.0.0',
                         'server.socket_port': 6543,
                        })

cherrypy.quickstart(Root(), '/', 'app.conf')
