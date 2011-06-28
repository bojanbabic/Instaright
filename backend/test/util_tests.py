import unittest, logging, ConfigParser, sys, os
from google.appengine.api import urlfetch
from users import UserUtil
from utils import StatsUtil,LinkUtil

class UrlUtilTest(unittest.TestCase):
        def _test_get_title(self):
                url="http://www.reddit.com/r/videos/"
                title=LinkUtil.getLinkTitle(url)
                self.assertEquals("videos", title)
                #test jpn chars
                url="http://blog.ohmynews.com/booking/168260"
                title=LinkUtil.getLinkTitle(url)
                #self.assertEquals("", title)
                url="https://appengine.google.com/logs?&app_idnstaright&version_id=49.350893459209639378"
                title=LinkUtil.getLinkTitle(url)
                self.assertEquals("Google Accounts", title)
        def _test_url(self):
                args=[u'545446@mail.gr', u'file%3A%2F%2Fuk.gizmodo.com%2F5805875%2Fthe-knock%2Bdown-drag%2Bout-fight-over-the-next-generation-of-batteries', u'The%20Knock-Down%2C%20Drag-Out%20Fight%20Over%20the%20Next%20Generation%20of%20Batteries', u'0.4.0.4']
                self.assertEquals(False,StatsUtil.checkUrl(args));
                args=[u'545446@mail.gr', u'chrome%3A%2F%2Fuk.gizmodo.com%2F5805875%2Fthe-knock%2Bdown-drag%2Bout-fight-over-the-next-generation-of-batteries', u'The%20Knock-Down%2C%20Drag-Out%20Fight%20Over%20the%20Next%20Generation%20of%20Batteries', u'0.4.0.4']
                self.assertEquals(False,StatsUtil.checkUrl(args));
                args=[u'545446@mail.gr', u'about%3A%2F%2Fuk.gizmodo.com%2F5805875%2Fthe-knock%2Bdown-drag%2Bout-fight-over-the-next-generation-of-batteries', u'The%20Knock-Down%2C%20Drag-Out%20Fight%20Over%20the%20Next%20Generation%20of%20Batteries', u'0.4.0.4']
                self.assertEquals(False,StatsUtil.checkUrl(args));
                args=[u'545446@mail.gr', u'ed2k%3A%2F%2Fuk.gizmodo.com%2F5805875%2Fthe-knock%2Bdown-drag%2Bout-fight-over-the-next-generation-of-batteries', u'The%20Knock-Down%2C%20Drag-Out%20Fight%20Over%20the%20Next%20Generation%20of%20Batteries', u'0.4.0.4']
                self.assertEquals(False,StatsUtil.checkUrl(args));
                args=[u'545446@mail.gr', u'liberator%3A%2F%2Fuk.gizmodo.com%2F5805875%2Fthe-knock%2Bdown-drag%2Bout-fight-over-the-next-generation-of-batteries', u'The%20Knock-Down%2C%20Drag-Out%20Fight%20Over%20the%20Next%20Generation%20of%20Batteries', u'0.4.0.4']
                self.assertEquals(False,StatsUtil.checkUrl(args));
                args=[u'545446@mail.gr', u'irc%3A%2F%2Fuk.gizmodo.com%2F5805875%2Fthe-knock%2Bdown-drag%2Bout-fight-over-the-next-generation-of-batteries', u'The%20Knock-Down%2C%20Drag-Out%20Fight%20Over%20the%20Next%20Generation%20of%20Batteries', u'0.4.0.4']
                self.assertEquals(False,StatsUtil.checkUrl(args));
                args=[u'545446@mail.gr', u'chrome-extension%3A%2F%2Fuk.gizmodo.com%2F5805875%2Fthe-knock%2Bdown-drag%2Bout-fight-over-the-next-generation-of-batteries', u'The%20Knock-Down%2C%20Drag-Out%20Fight%20Over%20the%20Next%20Generation%20of%20Batteries', u'0.4.0.4']
                self.assertEquals(False,StatsUtil.checkUrl(args));
                args=[u'545446@mail.gr', u'http%3A%2F%2Fuk.gizmodo.com%2F5805875%2Fthe-knock%2Bdown-drag%2Bout-fight-over-the-next-generation-of-batteries', u'The%20Knock-Down%2C%20Drag-Out%20Fight%20Over%20the%20Next%20Generation%20of%20Batteries', u'0.4.0.4']
                self.assertEquals(True,StatsUtil.checkUrl(args));

