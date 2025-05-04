def import_logs_from_file(file_path):
    with open(file_path, 'r') as f:
        for line in f:
            parse_log_line(line)
