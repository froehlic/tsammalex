<%inherit file="app.mako"/>

##
## define app-level blocks:
##
##<%block name="header">
##    <a href="${request.route_url('dataset')}">
##        <img src="${request.static_url('tsammalex:static/tsamma.png')}"/>
##   </a>
##</%block>
<%block name="brand">
    <a class="brand" href="${request.route_url('dataset')}">Tsammalex</a>
</%block>

${next.body()}
