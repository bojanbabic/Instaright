function jsonifyObject(o){
	var s="";
	var a = Array();
	$.each(o, function(){
			if (this.value.length > 0){
				a.push(quote_wrap(this.value));
			}
		});
	return bracket_wrap(a.join(','));
}
function jsonifyInstarightObject(o){
	var a = Array();
	a.push(quote_wrap(''));
	a.push(quote_wrap(o.link));
	a.push(quote_wrap(o.link_title.replace(/\"/g, "\\\"")));
	a.push(quote_wrap("0.1"));
	a.push(quote_wrap("bookmarklet"));
	a.push(quote_wrap(o.note.replace(/\"/g, "\\\"")));
	a.push(quote_wrap(o.share));
	
	return bracket_wrap(a.join(','));
}
function quote_wrap(word){
	return "\""+word+"\"";
}
function bracket_wrap(word){
	return "["+ word + "]";
}
function updated_string(dateUpdated){
	/* stupid hack need to remove this*/
	//localDate = new Date();
	//localOffset = new Date().getTimezoneOffset() * 60000;

	//utc = localDate.getTime() + localOffset;
	now=new Date();
	//now=new Date(utc);
	
	if (window.console && window.console.log){
		//console.log('utc:'+ utc);
		console.log("calculate post update: now:" + now + "("+now.getTime()+ ") post time: " + dateUpdated+ "("+dateUpdated.getTime()+")");
	}
	updated_ago = now.getTime() - dateUpdated.getTime();
	//console.info('date updated milis:' + dateUpdated + ' now:'+ now +' => updated ago:'+updated_ago);
	updated_ago_secs = Math.floor(updated_ago / 1000);
	updated_ago_mins = Math.floor(updated_ago / 1000 / 60);
	updated_ago_hours = Math.floor(updated_ago / 1000 / 60 / 60);
	updated_ago_string = 'now';
	if (updated_ago_hours > 1){
		updated_ago_string = updated_ago_hours + " hours ago";
	} 
	else if (updated_ago_hours > 0){
		updated_ago_string = "hour ago";
	}
	else if (updated_ago_mins > 1){
		updated_ago_string = updated_ago_mins + " minutes ago";
	}
	else if (updated_ago_mins > 0){
		updated_ago_string = "minute ago";
	}
	else if (updated_ago_secs > 1){
		updated_ago_string = updated_ago_secs + " seconds ago";
	}
	else if (updated_ago_secs >= 0){
		updated_ago_string = "now";
	} else {
		//console.info('dif is less then 1s');
	}
	if (window.console && window.console.log){
		console.log("updated ago:" + updated_ago_string);
	}
	return updated_ago_string;
}
/*$.fn.serializeObject = function(){
	var o = {};
	var a = this.serializeArray();
	$.each(a, function(){
			if (o[this.name] !== undefined){
				o[this.name].push(this.value || '');
			} else {
				o[this.name] = this.valiue || '';
			}
		});
	return o;

};
*/
