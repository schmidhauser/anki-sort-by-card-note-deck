# -*- coding: utf-8 -*-
# Copyright: (c) 2014 Teemu Pudas, (c) 2019 Andreas U. Schmidhauser.
# Please report issues to <https://github.com/schmidhauser>.
# License: GNU AGPLv3 <https://www.gnu.org/licenses/agpl.html>.

"""
SORT BY CARD TYPE, NOTE TYPE, OR DECK NAME

This addon makes the Card, Note, and Deck columns in the browser sortable.

If the (primary) sort key is the card type, then the secondary sort key is the note type; and vice versa. 

Sorting is case-insensitive. The search box cannot be empty.
"""

from aqt.browser import Browser
from anki.find import Finder
from anki.hooks import wrap
from aqt.utils import showInfo
from anki.consts import MODEL_CLOZE

DEBUG = False

def sortByCardType(self, query, order=False, _old=None):
	sortType = self.col.conf['sortType']
	if not order or sortType not in ("template", "note", "deck"):
		return _old(self, query, order)
		
	tokens = self._tokenize(query)
	preds, args = self._where(tokens)
	if preds is None:
		return []
	order, rev = self._order(order)
	sql = self._query(preds, "")
	if "c where " in sql:
		sql = sql.replace(" where", ", notes n where c.nid=n.id and", 1)
	values = "c.id, c.did, c.odid, n.id" if sortType == "deck" else "c.id, n.mid, c.ord, n.id"
	sql = sql.replace("select c.id", "select " + values, 1)
	try:
		cardInfo = self.col.db.all(sql, *args)
	except:
		# invalid grouping
		if DEBUG:
			origsql = self._query(preds, order)
			showInfo(sql + "\n" + origsql)
		return []
		
	# fetch each name only once
	cardNames = {}
	def getData(c):
		if sortType == "deck":
			if c.odid:
				# in a cram deck
				return ("%s (%s)" % (
					self.col.decks.name(c.did),
					self.col.decks.name(c.odid))).lower()
            # normal deck
			return self.col.decks.name(c.did).lower()
		else: 
			t = c.template()['name']
			m = c.model()
			if m['type'] == MODEL_CLOZE: 
				t += " %d" % (c.ord+1)
			t = t.lower()
			m = m['name'].lower()
			if sortType == "template":
				return (t, m)
			else:
				return (m, t)
	def cardName(x):
		type = x[1:3]
		if type not in cardNames:
			c = self.col.getCard(x[0])
			cardNames[type] = getData(c)
		return cardNames[type]
			
	cards = [(cardName(x), x[3], x[0]) for x in cardInfo] # tertiary sort key: note id
	cards.sort(reverse=rev)
	cards = [x[2] for x in cards]
	
	return cards
	
Finder.findCards = wrap(Finder.findCards, sortByCardType, "around")
	
def onSortChanged(self, idx, ord):
    type = self.model.activeCols[idx]
    noSort = ("question", "answer", "noteTags")
    if type in noSort:
        showInfo(_("Sorting on this column is not supported. Please "
                   "choose another."))
        type = self.col.conf['sortType']
    if self.col.conf['sortType'] != type:
        self.col.conf['sortType'] = type
        # default to descending for non-text fields
        if type == "noteFld":
            ord = not ord
        self.col.conf['sortBackwards'] = ord
    else:
        if self.col.conf['sortBackwards'] != ord:
            self.col.conf['sortBackwards'] = ord
            self.model.reverse()
    self.setSortIndicator()
	
Browser.onSortChanged = onSortChanged
