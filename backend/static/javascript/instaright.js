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
	a.push(quote_wrap(o.login));
	a.push(quote_wrap(o.link));
	a.push(quote_wrap(o.link_title));
	a.push(quote_wrap("0.1"));
	a.push(quote_wrap("bookmarklet"));
	a.push(quote_wrap(o.note));
	a.push(quote_wrap(o.share));
	
	return bracket_wrap(a.join(','));
}
function quote_wrap(word){
	return "\""+word+"\"";
}
function bracket_wrap(word){
	return "["+ word + "]";
}
function updated_string(dateUpdated, now){
	/* stupid hack need to remove this*/
	updated_ago = now - dateUpdated;
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
