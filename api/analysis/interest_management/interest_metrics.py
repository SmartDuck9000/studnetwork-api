def interest_distance(vec1, vec2):
    """equivalent to manhattan distance for 2 interest vectors"""
    return sum(abs(vec1[i] - vec2[i]) for i in range(len(vec1)))


def weighed_interest_distance(vec1, vec2, weights):
    """interest distance with weights for each dimension"""
    return sum(abs(vec1[i] - vec2[i]) * 1 / weights[i] for i in range(len(vec1)))
