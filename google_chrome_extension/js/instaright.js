function insta_notify(response,isNotification){
	var notification_details = mapResponse(response);
	if (isNotification){
		var notification = webkitNotifications.createNotification(
			notification_details["icon"],
			notification_details["status"],
			notification_details["message"]
		);
		notification.show();
		setTimeout(function(){notification.cancel();}, 1700);
	} else {

		$('body').html("");
		$('body').append('<table style="float: left; width:300px;"><tbody><tr><td><img src="'+notification_details["icon"]+'"></td><td><p style="margin-top:5px;"><b>'+notification_details["status"]+'</b></p><p style="margin-top:-5px">'+notification_details["message"]+'</p></td></tr></tbody></table>');
		setTimeout(function(){window.close();}, 1500);
	}
}
function sendToInstapaper(loc, isNotification){
	instapaper_password = localStorage["instapaper_password"];
	instapaper_account=localStorage["instapaper_account"];
	data = 'username='+instapaper_account+'&password='+instapaper_password+'&url='+loc;

	$.ajax({
		type:'POST', 
		url:'http://www.instapaper.com/api/add', 
		data: data,
		async: false,
		success: function(response){
				insta_notify(response, isNotification);
			},
			error: function(xhr, ajaxOptions, error){
				insta_notify(xhr.status, isNotification);
			},
		});
}
function sendToBackend(loc, title){
	var instapaper_password = localStorage["instapaper_password"];
	var instapaper_account=localStorage["instapaper_account"];
	data="[\""+instapaper_account+"\",\""+encodeURIComponent(loc)+"\",\""+title+"\",\"0.1\",\"chrome\"]";
	$.ajax({
		type:'POST', 
		url:'http://instaright.appspot.com/rpc', 
		dataType: "json",
		data: data,
		success: function(response){
			localStorage["response"]=response;
		}
	});
			
}
function mapResponse(response){
		if (response == '400'){
			return {'status':"Bad request", 'message':"Request has not been valid",'icon':"img/instaright.png"}
		} else if (response == '403'){
			return {'status':"Invalid credentials", 'message':"Please check your user name and password",'icon':"img/instaright.png"}
		} else if (response == '500'){
			return {'status':"Service error", 'message':"Third party service encountered an error.",'icon':"img/instaright.png"}
		} else if (response == '201'){
			return {'status':"Success", 'message':"Your request has been processed",'icon':"img/instaright.png"}
		}
		var response_message = localStorage("response");
		/*var firstBookmark = localStorage("noBookmarks");
		var alert_status;
		var alert_message;
		var alert_icon;
		var firstRun = false;
		firstRun = localStorage("firstrun");
		var version = -1;
		version = localStorage("version");
		if (firstBookmark && !firstRun && version == com.appspot.model.currentVersion){
			alert_status = localStorage("alert_congrats");
			alert_message = localStorage("alert_first_message");

			alert_icon = "chrome://instaright/skin/champagne.png"");
			com.appspot.model.prefs.setBoolPref("noBookmarks", false);
			return;
		}
		var cachedValue = localStorage("badge_cache");
		var expires = localStorage("badge_expiration");
		var now = new Date();
		var exp_time = new Date(parseInt(expires));
		if  (now.getTime() < exp_time.getTime()){
			// just set backend response
			response_message = cachedValue;
		}
		// based on backend repsonse set icon, status and message
		if (response_message == ''){
			alert_status=localStorage("alert_instaright");
			alert_message=alert_message;
			alert_icon="chrome://instaright/skin/instapaper_mod.png";
		}
		else if (response_message == 'hny'){
			alert_status=alert_message;
			alert_message=localStorage("alert_hny");
			alert_icon="chrome://instaright/skin/hny.png";
		}
		else if (response_message == '1000'){
			alert_status=alert_message;
			alert_message=localStorage("alert_onek");
			alert_icon="chrome://instaright/skin/onek.png";
		}
		else if (response_message == '5000'){
			alert_status=alert_message;
			alert_message=localStorage("alert_fivek");
			alert_icon="chrome://instaright/skin/fivek.png";
		}
		else if (response_message == '10000'){
			alert_status=alert_message;
			alert_message=localStorage("alert_tenk");
			alert_icon="chrome://instaright/skin/tenk.png";
		}
		else if (response_message == '1'){
			alert_status=alert_message;
			alert_message=localStorage("alert_trophy");
			alert_icon="chrome://instaright/skin/dfirst.png";
		}
		else if (response_message == '2'){
			alert_status=alert_message;
			alert_message=localStorage("alert_trophy");
			alert_icon="chrome://instaright/skin/dsecond.png";
		}
		else if (response_message == '3'){
			alert_status=alert_message;
			alert_message=localStorage("alert_trophy");
			alert_icon="chrome://instaright/skin/dthird.png";
		}
		else if (response_message == '5'){
			alert_status=alert_message;
			alert_message=localStorage("alert_usage");
			alert_icon="chrome://instaright/skin/5usage.png";
		}
		else if (response_message == '25'){
			alert_status=alert_message;
			alert_message=localStorage("alert_sl");
			alert_icon="chrome://instaright/skin/sl25.png";
		}
		else if (response_message == '55'){
			alert_status=alert_message;
			alert_message=localStorage("alert_sl");
			alert_icon="chrome://instaright/skin/sl55.png";
		}
		else if (response_message == '65'){
			alert_status=alert_message;
			alert_message=localStorage("alert_sl");
			alert_icon="chrome://instaright/skin/sl65.png";
		}
		else if (response_message == '105'){
			alert_status=alert_message;
			alert_message=localStorage("alert_sl");
			alert_icon="chrome://instaright/skin/sl105.png";
		}
		else if (response_message == 'ny'){
			alert_status=alert_message;
			alert_message=localStorage("alert_ny");
			alert_icon="chrome://instaright/skin/ny.png";
		}
		else if (response_message == 'robot'){
			alert_status=alert_message;
			alert_message=localStorage("alert_gadget");
			alert_icon="chrome://instaright/skin/robot.png";
		}
		else if (response_message == 'yen'){
			alert_status=alert_message;
			alert_message=localStorage("alert_economy");
			alert_icon="chrome://instaright/skin/yen.png";
		}
		else if (response_message == 'movie'){
			alert_status=alert_message;
			alert_message=localStorage("alert_movie");
			alert_icon="chrome://instaright/skin/movie.png";
		}
		else if (response_message == 'news'){
			alert_status=alert_message;
			alert_message=localStorage("alert_news");
			alert_icon="chrome://instaright/skin/news.png";
		}
		else if (response_message == 'wiki'){
			alert_status=alert_message;
			alert_message=localStorage("alert_wiki");
			alert_icon="chrome://instaright/skin/wiki.png";
		}
		else if (response_message == 'sport'){
			alert_status=alert_message;
			alert_message=localStorage("alert_sport");
			alert_icon="chrome://instaright/skin/sport.png";
		}
		else if (response_message == 'music'){
			alert_status=alert_message;
			alert_message=localStorage("alert_music");
			alert_icon="chrome://instaright/skin/music.png";
		}
		else if (response_message == 'new_domain'){
			alert_status=alert_message;
			alert_message=localStorage("alert_domain");
			alert_icon="chrome://instaright/skin/new_domain.png";
		}
                else {
			alert_status=localStorage("alert_instaright");
			alert_message=alert_message;
			alert_icon="chrome://instaright/skin/instapaper_mod.png";
		}*/
}
function sendToService(info, tab, isNotification){
			
	try{
		var page_url = tab.url;
		var title = tab.title;
		if (info != null){
			var linkHover = info.linkUrl;
		}
		var loc = page_url;
		if (typeof linkHover != 'undefined'){
			loc = linkHover;
		}
		if (typeof isNotification == 'undefined'){
			isNotification = true;
		}
		sendToBackend(loc, title);
		sendToInstapaper(loc, isNotification);
	}catch(e){}
}
var contexts = ["page","link","editable","image","video",
                "audio"];
for (var i = 0; i < contexts.length; i++) {
  var context = contexts[i];
  var title = "Instaright it!";
  var id = chrome.contextMenus.create({"title": title, "contexts":[context],
                                       "onclick": sendToService});
}
