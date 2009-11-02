cd $HOME/d/work/_ff_extensions/my_ff/build/instaright/
zip -r chrome/instaright.zip content/ skin/ 
mv chrome/instaright.zip chrome/instaright.jar
zip -r instaright.zip chrome/ install.js  install.rdf defaults/  
mv instaright.zip instaright.xpi
