def read(filename):
    """
    Reads in a corestick file and returns a dictionary keyed by core_id.
    Layer interface depths are positive and are relative to the lake bottom.
    depths are returned in meters. Northing and Easting are typically in the
    coordinate system used in the rest of the lake survey. We ignore the
    width fields in the file.
    """

    cores = {}
    with open(filename) as f:
        units = f.readline().strip('\r\n').lower()

        if units not in ['feet', 'meters', 'meter']:
            raise NotImplementedError('Only units of FEET and METERS/METER are supported ')

        conv_factor = 1.0

        if units == 'feet':
            conv_factor = 0.3048

        f.readline()
        for line in f.readlines():
            fields = line.split()
            core_id = fields[2]
            data = {}
            data['easting'] = float(fields[0])
            data['northing'] = float(fields[1])
            data['layer_interface_depths'] = [
                float(fields[i]) * conv_factor
                for i in range(5, len(fields), 4)
            ]
            data['layer_colors'] = [
                int(fields[i]) for i in range(6, len(fields), 4)]
            cores[core_id] = data

    return cores
