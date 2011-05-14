function include(file){
	var script= document.createElement('element');
	script.src = file;
	script.type = 'text/javascript';
	script.defer = true;
	
	document.getElementsByTagName("head").item(0).appendChild(script);
}
include('https://ajax.googleapis.com/ajax/libs/jquery/1.4.4/jquery.min.js')
