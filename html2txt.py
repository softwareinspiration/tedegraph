#!/usr/bin/env python
# encoding: utf-8
from urllib.request import urlopen, urlretrieve, urlparse, urlunparse
from urllib.parse import urljoin
import sys
from bs4 import BeautifulSoup
import bs4
import nltk.util
import re
import nltk
from nltk.tokenize import word_tokenize
from ebooklib import epub
from subprocess import check_output
import os
import codecs

images_dict = {}

def nodeToSentences(node):
  # converts html node (tag) to list of sentences

  if node is None:
    print ("node is None")
    exit(0)

  # remove uninteresting tags
  for t in node.find_all(["script", "noscript", "style"]):
    t.decompose() # t.extract() is similar method 

  for idx, img in enumerate(node.find_all("img")):
      img.replaceWith("tdg_img_" + str(idx))
      img_key = "tdg_img_{}".format(idx)
      images_dict[img_key] = img["src"]

  all_nav_strings = [x for x in node.find_all(text=True) if x.strip() != "" if not type(x) is bs4.Comment]
  
  buffer = ""
  tokenized_strings = []
  for idx, nav_s in enumerate(all_nav_strings): # before it was enumerating node.stripped_strings
    s = nav_s.strip()
    s = s.replace("\r", "")

    try:
      s_next = all_nav_strings[idx + 1] # next navigable string
    except:
      s_next = None

    # pridame string s do bufferu
    if s.startswith(",") or s.startswith(".") or buffer == "":
      buffer += s
    else:
      buffer += " " + s

    # tokenize the content of the buffer and empty the buffer.
    if s.endswith(".") or s_next is None or separateStrings(nav_s, s_next):
      # up: konec věty nebo konec textu nebo nav_s a s_next budou rozděleny
      tokenizer = nltk.data.load('nltk:tokenizers/punkt/english.pickle')
      buffer = buffer.replace("\n", " ")
      buffer = re.sub(" +", " ", buffer) # jednu nebo více mezer nahradíme jednou mezerou
      sentences = tokenizer.tokenize(buffer)
      for sen in sentences:
        tokenized_strings.append(sen)
      buffer = ""

  return tokenized_strings

def separateStrings(s1, s2):
  #common = list(set([x.name for x in s1.parents if x in s2.parents])) # spolecne uzly s1 a s2
  onlys1 = [x.name for x in s1.parents if not x in s2.parents] # uzly pouze nad s1
  onlys2 = [x.name for x in s2.parents if not x in s1.parents] # uzly pouze nad s2
  # seznam tagu, ktere urcite nechaji s1 a s2 rozdelene, pokud jsou pouze nad jednim ci druhym stringem, je
  # hned jasne, ze nema smysl spojovat s1 a s2 v jednu vetu
  separatingTags = [ "h1", "h2", "h3", "h4", "h5", "h6", "h7", "li", "ol", "ul", "table", "tr", "th", "td", "div", "p" ]
  for x in separatingTags:
    if x in onlys1 or x in onlys2:
      return True
  return False

def getSoupFromUrl(url):
  if url.startswith('http'):
    html = urlopen(url).read().decode('utf-8', 'ignore')
    soup = BeautifulSoup(html, features = "html.parser")
  elif url.endswith(".html"): # html file
    html = open(url, 'r')
    soup = BeautifulSoup(html.read())
    html.close()
  elif url.endswith(".epub"): # epub file
    book = epub.read_epub(url)
    pages = [page for page in book.items if type(page) == epub.EpubHtml]
    soup = BeautifulSoup("<html><head></head><body></body></html>")
    for p in pages:
      s = BeautifulSoup(p.content)
      part = s.html.body
      part.name = "p"
      soup.html.body.append(part)
      print (len(soup.html.body))
  elif url.endswith(".pdf"):
    first_page = input("First page: ")
    last_page = input("Last page: ")
    output = check_output(["pdftotext", "-f", first_page, "-l", last_page, "-htmlmeta", "-nopgbrk", "-layout", url, "-"])
    #output = check_output(["pdftotext", "-htmlmeta", "-nopgbrk", url, "-"])
    soup = BeautifulSoup(output)
  elif url.endswith(".txt"):
    text = open(url, 'r').readlines()
    title = url.replace(".txt", "")
    soup = BeautifulSoup("<html><title>" + title + "</title><head></head><body><div></div></body></html>")
    soup.html.body.div.append("".join(text))
    print (len(soup.html.body))
  else:
    return
  return soup

def saveArticle(url, title, sentences):

  if not os.path.exists(title):
      os.makedirs(title)

  fileName = "0000000.txt"

  i = 0  # number of file

  pattern = re.compile("tdg_img_\d+")

  for sentence in sentences:
    if pattern.match(sentence):
      img_url = images_dict[sentence]
          
      img_file_name = "%07d" % i
      if url.startswith("https") and not img_url.startswith("https"):
          urlretrieve("https:" + img_url, os.path.join(title, img_file_name))
      elif url.startswith("http") and not img_url.startswith("http"):
          urlretrieve("http:" + img_url, os.path.join(title, img_file_name))
      else:
          urlretrieve(img_url, os.path.join(title, img_file_name))
      fileName = "%07d.txt" % i 
      i = i + 1
      continue

    with codecs.open(os.path.join(title, fileName), "a", encoding="utf-8") as f:
      f.write(sentence + "\n")