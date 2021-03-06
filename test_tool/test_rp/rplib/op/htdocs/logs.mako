<%
  def display_log(testid, logs):
    el = ["<ul>"]
    for name, path in logs:
        el.append('<li><a href="/log%s/%s">%s</a>' % (testid, path, name))
    el.append("</ul>")
    return "\n".join(el)
%>

<!DOCTYPE html>
<html>
<head>
  <title>OpenID Certification OP Test</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- Bootstrap -->
  <link href="/static/bootstrap/css/bootstrap.min.css" rel="stylesheet"
        media="screen">
  <link href="/static/style.css" rel="stylesheet" media="all">

  <!-- HTML5 shim and Respond.js IE8 support of HTML5 elements and media queries -->
  <!--[if lt IE 9]>
  <script src="../../assets/js/html5shiv.js"></script>
  <script src="../../assets/js/respond.min.js"></script>
  <![endif]-->
</head>
<body>
<div class="container">
  <!-- Main component for a primary marketing message or call to action -->
  <div class="jumbotron">
    <h1>OpenID Certification OP Test logs</h1>
    <h3>A list of test results that are saved on disc:</h3>
    ${display_log(testid, logs)}
      % if testid != '':
          <%
              cl_url = "/clear%s" % (testid)
              tar_url = "/mktar%s" % (testid)
              tar_file = "{}.tgz".format(testid[1:])
              %>
          <p>
              <a href="${cl_url}"><b>Clear all test logs</b></a>
          </p>
          <p>
              <a href="${tar_url}" download="${tar_file}"><b>Download tar file</b></a>
          </p>
      % endif
  </div>

</div> <!-- /container -->
<!-- jQuery (necessary for Bootstrap's JavaScript plugins) -->
<script src="/static/jquery.min.1.9.1.js"></script>
<!-- Include all compiled plugins (below), or include individual files as needed -->
<script src="/static/bootstrap/js/bootstrap.min.js"></script>

</body>
</html>