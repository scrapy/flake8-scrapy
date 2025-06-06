class IssueFinder(object):
    msg_code = ""
    msg_info = ""

    @property
    def message(self):
        return "{} {}".format(self.msg_code, self.msg_info)

    def find_issues(self, node):
        raise NotImplementedError
