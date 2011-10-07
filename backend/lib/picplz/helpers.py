import itertools
import logging
from google.appengine.api import urlfetch
import time, datetime
from uuid import uuid4
import mimetools
import mimetypes
from cStringIO import StringIO
import urllib
import urllib2

class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = "instaright."+str(uuid4())+"."+str(int(time.mktime(datetime.datetime.now().timetuple())))
        return
    
    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return
    
    def add_url(self, fieldname, title, url, mimetype=None):
        body=None
        try:
	        response = urlfetch.fetch(url)
                if response.status_code == 200:
                        logging.info('fetched %s ' % len(response.content))
                        body = response.content
	        #body = urllib2.urlopen(url)
        except:
                logging.error("can't load url stram %s" % url)
	if mimetype is None:
		mimetype = 'application/octet-stream'
	self.files.append((fieldname, title, mimetype, body))
    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary
        
        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              '',
              value,
            ]
            for name, value in self.form_fields
            )
        
        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )
        
        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        #return '\r\n'.join(["%s" % el for el in flattened])
        return '\r\n'.join([el.decode('string_escape') for el in flattened])