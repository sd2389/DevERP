# DevERP/views.py
from django.http import HttpResponse

def handler404(request, exception):
    html = """
    <html>
    <head>
        <title>Page Not Found</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row">
                <div class="col-md-8 offset-md-2">
                    <div class="card">
                        <div class="card-header bg-danger text-white">
                            <h4>Page Not Found (404)</h4>
                        </div>
                        <div class="card-body">
                            <p>The page you requested could not be found.</p>
                            <p>Path: {0}</p>
                            <a href="/" class="btn btn-primary">Back to Home</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """.format(request.path)
    return HttpResponse(html, status=404)

def handler500(request, *args, **kwargs):
    html = """
    <html>
    <head>
        <title>Server Error</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row">
                <div class="col-md-8 offset-md-2">
                    <div class="card">
                        <div class="card-header bg-danger text-white">
                            <h4>Server Error (500)</h4>
                        </div>
                        <div class="card-body">
                            <p>Something went wrong on our end.</p>
                            <p>Please try again later.</p>
                            <a href="/" class="btn btn-primary">Back to Home</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html, status=500)