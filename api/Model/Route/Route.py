from Model.Route.route_data import main_page_file


class Route:
    html_files = {'/': main_page_file}

    def getFile(self, url):
        return self.html_files[url]
