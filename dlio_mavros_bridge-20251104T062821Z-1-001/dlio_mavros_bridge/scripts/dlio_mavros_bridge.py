#!/usr/bin/env python3

import rospy
import math
import tf
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped, TwistStamped
from mavros_msgs.msg import PositionTarget
from sensor_msgs.msg import Imu
from tf.transformations import euler_from_quaternion, quaternion_from_euler

class DlioMavrosBridge:
    def __init__(self):
        rospy.init_node('dlio_mavros_bridge', anonymous=True)
        
        # Parameters
        self.odom_frame = rospy.get_param('~odom_frame', 'robot/odom')
        self.base_frame = rospy.get_param('~base_frame', 'robot/base_link')
        self.publish_rate = rospy.get_param('~publish_rate', 10.0)  # Hz
        
        # Publishers
        self.vision_pose_pub = rospy.Publisher('/mavros/vision_pose/pose', PoseStamped, queue_size=10)
        self.vision_speed_pub = rospy.Publisher('/mavros/vision_speed/speed_twist', TwistStamped, queue_size=10)
        self.setpoint_raw_pub = rospy.Publisher('/mavros/setpoint_raw/local', PositionTarget, queue_size=10)
        
        # Subscribers
        rospy.Subscriber('/robot/dlio/odom_node/odom', Odometry, self.odom_callback)
        
        # TF listener
        self.tf_listener = tf.TransformListener()
        
        # Variables
        self.last_odom = None
        self.last_time = None
        
        # Main loop
        rate = rospy.Rate(self.publish_rate)
        while not rospy.is_shutdown():
            if self.last_odom is not None:
                self.publish_vision_data()
            rate.sleep()
    
    def odom_callback(self, msg):
        self.last_odom = msg
        self.last_time = rospy.Time.now()
    
    def publish_vision_data(self):
        # Publish vision pose
        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.last_odom.header.stamp
        pose_msg.header.frame_id = 'map'  # MAVROS expects 'map' frame
        
        # Transform pose if necessary (from odom to map frame)
        try:
            # If you have a map->odom transform, apply it here
            # For simplicity, we'll assume odom is the map frame in this example
            pose_msg.pose = self.last_odom.pose.pose
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException) as e:
            rospy.logwarn("TF exception: %s", e)
            pose_msg.pose = self.last_odom.pose.pose
        
        self.vision_pose_pub.publish(pose_msg)
        
        # Publish vision speed
        twist_msg = TwistStamped()
        twist_msg.header.stamp = self.last_odom.header.stamp
        twist_msg.header.frame_id = 'base_link'
        twist_msg.twist = self.last_odom.twist.twist
        self.vision_speed_pub.publish(twist_msg)
        
        # Publish setpoint (optional, for position control)
        setpoint_msg = PositionTarget()
        setpoint_msg.header.stamp = self.last_odom.header.stamp
        setpoint_msg.coordinate_frame = PositionTarget.FRAME_LOCAL_NED
        setpoint_msg.type_mask = (PositionTarget.IGNORE_VX + 
                                PositionTarget.IGNORE_VY + 
                                PositionTarget.IGNORE_VZ +
                                PositionTarget.IGNORE_AFX +
                                PositionTarget.IGNORE_AFY +
                                PositionTarget.IGNORE_AFZ +
                                PositionTarget.IGNORE_YAW_RATE)
        
        setpoint_msg.position.x = pose_msg.pose.position.x
        setpoint_msg.position.y = pose_msg.pose.position.y
        setpoint_msg.position.z = pose_msg.pose.position.z
        
        # Convert quaternion to yaw
        orientation_q = pose_msg.pose.orientation
        _, _, yaw = euler_from_quaternion([orientation_q.x, 
                                          orientation_q.y, 
                                          orientation_q.z, 
                                          orientation_q.w])
        setpoint_msg.yaw = math.degrees(yaw)
        
        self.setpoint_raw_pub.publish(setpoint_msg)

if __name__ == '__main__':
    try:
        bridge = DlioMavrosBridge()
    except rospy.ROSInterruptException:
        pass
