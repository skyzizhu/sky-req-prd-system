/* V2 project entry; no single-manifest runtime. */
(function(){
  var narrow=matchMedia('(max-width: 800px)');
  function setSidebar(collapsed){document.body.classList.toggle('sidebar-collapsed',collapsed);document.getElementById('sidebar-expand').setAttribute('aria-expanded',String(!collapsed));}
  setSidebar(narrow.matches);
  document.getElementById('sidebar-toggle').onclick=function(){setSidebar(true);};
  document.getElementById('sidebar-expand').onclick=function(){setSidebar(false);};
  narrow.addEventListener('change',function(e){setSidebar(e.matches);});
  document.getElementById('menu').addEventListener('click',function(e){if(narrow.matches && e.target.closest('a'))setSidebar(true);});
  function boot(){if(!window.__PS_PROJECT){document.getElementById('content').textContent='缺少 V2 项目数据，请重新构建。';return;}PS.bootProject();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
