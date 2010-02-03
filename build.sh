cd $HOME/d/work/_ff_extensions/instaright/
zip -vr chrome/instaright.zip content/ skin/  -x "*.svn*"
mv chrome/instaright.zip chrome/instaright.jar
zip -vr instaright.zip chrome/ install.js  install.rdf chrome.manifest defaults/   -x "*.svn*"
mv instaright.zip instaright.xpi
