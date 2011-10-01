import logging
#urllib.getproxies_macosx_sysconf = lambda: {}

class Cast:
        @classmethod
        def toInt(cls, string, default):
                try:
                        return int(string)
                except ValueError:
                        logging.info('int parse error return default value %s' % default)
                        return default

        @classmethod
        def toFloat(cls, string, default):
                try:
                        return float(string)
                except:
                        return default
                
BADGES_VERSION={'0.4.0.4':['news','yen','movie', 'robot']}
TRESHOLD_VERSION='0.4.0.4'
class Version:
        @staticmethod
        def validateVersion(version,badge):
                if version is None:
                        logging.info('Older version of addon!')
                        return False
                logging.info('checking version %s ' % version)
                compRes=Version.compareVersions(version, TRESHOLD_VERSION)
                # all versions after 0.4.0.4 should be able to handle all badges
                if compRes >= 0:
                        logging.info('valid version allowing badge %s' % badge)
                        return True
                badges=BADGES_VERSION[version]
                if badges is not None and badge in badges:
                        logging.info('valid badge %s for version %s' %( badge, version))
                        return True
                else:
                        logging.info('can\'t find badges for %s' % version)
                logging.info('Older version of addon!')
                return False
                
        @staticmethod
        def compareVersions(v1, v2):
                if v1 is None and v2 is not None:
                        return -1
                if v1 is not None and v2 is None:
                        return 1
                if v1 is None and v2 is None:
                        return 0
                #v1Tokens=v1.split('.')
                #v2Tokens=v2.split('.')
                for x,y in zip(v1, v2):
                        if x < y: return -1
                        if x > y: return 1
                return 0


