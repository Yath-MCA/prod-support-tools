var fm=[],fi=-1;
var currentAnchorIndex=0;
var delmergeSection=null;
var delmergeRows=[];

function af(){
var t=(document.getElementById('tf').value||'').toLowerCase();
var s=document.getElementById('sf').value;
var p=document.getElementById('pf').value;
var v=0;

document.querySelectorAll('#main-report-table tbody tr').forEach(function(r){

var ok=(
(!t||r.textContent.toLowerCase().includes(t))&&
(!s||r.dataset.status===s)&&
(!p||(r.dataset.parent||'').includes(p))
);

r.style.display=ok?'':'none';

if(ok)v++;

});

document.getElementById('rc').textContent=v+' rows shown';
}

function bd(){

var ss=document.getElementById('sf');
var ps=document.getElementById('pf');

var sv=new Set();
var pv=new Set();

document.querySelectorAll('#main-report-table tbody tr')
.forEach(function(r){

if(r.dataset.status){
sv.add(r.dataset.status);
}

if(r.dataset.parent&&r.dataset.parent!=='—'){
pv.add(r.dataset.parent);
}

});

[...sv].sort().forEach(function(s){

var o=document.createElement('option');

o.value=s;
o.textContent=s;

ss.appendChild(o);

});

[...pv].sort().forEach(function(s){

var o=document.createElement('option');

o.value=s;
o.textContent=s;

ps.appendChild(o);

});

document.getElementById('rc').textContent=
document.querySelectorAll('#main-report-table tbody tr').length+
' rows shown';

}

function df(){

var q=(document.getElementById('fi').value||'').toLowerCase();

if(!q){
cf();
return;
}

fm=[];
fi=-1;

document.querySelectorAll('#main-report-table tbody tr')
.forEach(function(r){

if(
r.style.display!=='none'&&
r.textContent.toLowerCase().includes(q)
){
fm.push(r);
}

});

document.getElementById('fc').textContent=fm.length+' found';

if(fm.length){
fi=0;
sm();
}

}

function sm(){

fm.forEach(function(r){
r.classList.remove('ring');
});

if(fi>=0&&fi<fm.length){

fm[fi].classList.add('ring');

fm[fi].scrollIntoView({
block:'center',
behavior:'smooth'
});

}

}

function fn(){

if(!fm.length)return;

fi=(fi+1)%fm.length;

sm();

}

function fp(){

if(!fm.length)return;

fi=(fi-1+fm.length)%fm.length;

sm();

}

function cf(){

document.getElementById('fi').value='';

fm=[];
fi=-1;

document.getElementById('fc').textContent='';

document.querySelectorAll('#main-report-table tbody tr')
.forEach(function(r){

r.classList.remove('ring');

});

}

function initDelmergeRows(){

delmergeSection=document.querySelector('.delmerge-view');

if(!delmergeSection)return;

delmergeRows=Array.prototype.slice.call(
delmergeSection.querySelectorAll('tbody tr[data-anchor]')
);

}

function focusHtmlView(anchor){

if(!delmergeSection)return;

var targetRow=null;

delmergeRows.forEach(function(row){

var match=!anchor||row.dataset.anchor===anchor;

row.style.display=match?'':'none';

row.classList.toggle('ring',match);

if(match&&!targetRow){
targetRow=row;
}

});

if(targetRow){

targetRow.scrollIntoView({
block:'center',
behavior:'smooth'
});

}

}

function getVisibleAnchorRows(){

return delmergeRows.filter(function(row){

return row.style.display!=='none';

});

}

function gotoAnchorRow(index){

var rows=getVisibleAnchorRows();

if(!rows.length)return;

if(index<0){
index=0;
}

if(index>=rows.length){
index=rows.length-1;
}

currentAnchorIndex=index;

var row=rows[currentAnchorIndex];

focusHtmlView(row.dataset.anchor||'');

}

function gotoPrevVisibleAnchor(){

gotoAnchorRow(currentAnchorIndex-1);

}

function gotoNextVisibleAnchor(){

gotoAnchorRow(currentAnchorIndex+1);

}

function bindMainReportClicks(){

document.querySelectorAll('#main-report-table tbody tr')
.forEach(function(r){

r.addEventListener('dblclick',function(){

focusHtmlView(r.dataset.anchor||'');

});

});

}

function toggleDelmergeDel(mode){

var section=document.querySelector('.delmerge-view');

if(!section)return;

if(mode==='hide'){
section.classList.add('hide-del');
}else{
section.classList.remove('hide-del');
}

}

function toggleHtmlView(mode){

var previews=document.querySelectorAll('.html-preview');
var raws=document.querySelectorAll('.html-raw');

if(mode==='preview'){

previews.forEach(function(el){
el.style.display='block';
});

raws.forEach(function(el){
el.style.display='none';
});

}else{

previews.forEach(function(el){
el.style.display='none';
});

raws.forEach(function(el){
el.style.display='block';
});

}

}

function initReport(){

bd();

initDelmergeRows();

bindMainReportClicks();

}

window.onload=initReport;